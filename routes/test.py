from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
import re
from database import get_db
from models import (
    User, UserRole, Question, TestAttempt, TestStatus,
    Answer, Score, InterpretedResult, Section, SectionProgress, SectionStatus
)
from auth.dependencies import get_current_user, require_role
from services.scoring import store_scores
from services.gemini_interpreter import generate_and_save_interpretation

router = APIRouter(prefix="/test", tags=["test"])

# Test configuration constants
TOTAL_QUESTIONS = 35  # Total questions across all sections (7 questions × 5 sections)
QUESTIONS_PER_SECTION = 7  # Questions per section
TOTAL_SECTIONS = 5  # Total number of sections

require_student = require_role([UserRole.STUDENT])
require_student_or_counsellor = require_role([UserRole.STUDENT, UserRole.COUNSELLOR])


class OptionItem(BaseModel):
    key: str
    text: str


class QuestionResponse(BaseModel):
    question_id: int
    question_text: str
    options: List[OptionItem]

    class Config:
        from_attributes = True


def parse_options_to_array(options_string: Optional[str]) -> List[OptionItem]:
    """
    Parse options string to array format.
    Handles formats like:
    - "A) Option A, B) Option B, C) Option C, D) Option D"
    - JSON format
    - Simple comma-separated with letter prefixes
    """
    if not options_string:
        return []
    
    # Try to parse as JSON first
    try:
        parsed = json.loads(options_string)
        if isinstance(parsed, list):
            # If it's already a list, convert to OptionItem format
            result = []
            for item in parsed:  # Process all items (can be 4 or 5)
                if isinstance(item, dict):
                    key = item.get('key', item.get('value', ''))
                    text = item.get('text', item.get('label', ''))
                    if key and text:
                        result.append(OptionItem(key=str(key).upper(), text=str(text).strip()))
                elif isinstance(item, str):
                    # Handle string items like "A) Text"
                    match = re.match(r'^([A-E])[\)\.]\s*(.+)$', item.strip(), re.IGNORECASE)
                    if match:
                        result.append(OptionItem(key=match.group(1).upper(), text=match.group(2).strip()))
            return result  # Return all parsed options
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Parse string format like "A) Strongly Disagree, B) Disagree, C) Neutral, D) Agree, E) Strongly Agree"
    result = []
    
    # Split by comma, but be smart about it - look for pattern ", A)", ", B)", etc.
    # This handles cases where option text might contain commas
    parts = re.split(r',\s*(?=[A-E][\)\.])', options_string)
    
    # Parse each part with pattern: ^([A-E])[\)\.]\s*(.+)$
    option_pattern = re.compile(r'^([A-E])[\)\.]\s*(.+)$', re.IGNORECASE)
    
    for part in parts:
        trimmed_part = part.strip()
        if not trimmed_part:
            continue
        
        match = option_pattern.match(trimmed_part)
        if match:
            key = match.group(1).upper()
            text = match.group(2).strip()
            if key and text:
                result.append(OptionItem(key=key, text=text))
    
    # If no options were parsed with the above method, try alternative parsing
    if len(result) == 0:
        # Try a more permissive regex that matches anywhere in the string
        pattern = r'([A-E])[\)\.]\s*([^,]+?)(?=\s*[A-E][\)\.]|$)'
        matches = re.finditer(pattern, options_string, re.IGNORECASE)
        
        for match in matches:
            key = match.group(1).upper()
            text = match.group(2).strip()
            if key and text:
                result.append(OptionItem(key=key, text=text))
    
    # Return all parsed options (can be 4 for MCQ or 5 for Likert scale)
    # Do NOT create placeholder options - if parsing fails, return empty array
    return result


class TestStartResponse(BaseModel):
    test_attempt_id: int
    status: str
    started_at: datetime
    total_questions: int

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    selected_option: str


class SubmitAnswersRequest(BaseModel):
    attempt_id: int
    answers: List[AnswerSubmit]


class TestResultResponse(BaseModel):
    total_questions: int
    correct_answers: int
    percentage: float
    status: str


class InterpretationResponse(BaseModel):
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    career_clusters: List[str]
    risk_level: str
    readiness_status: str
    action_plan: List[str]
    overall_percentage: float
    total_questions: int
    correct_answers: int
    is_ai_generated: bool
    readiness_explanation: str
    risk_explanation: str
    career_direction: str
    career_direction_reason: str
    roadmap: Dict


class TestStatusResponse(BaseModel):
    test_attempt_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_questions: int
    answered_questions: int
    completed_sections: List[int]  # List of completed section order_index values (1-5)
    current_section: Optional[int]  # Current section order_index (1-5) or None
    total_sections: int  # Total number of sections (always 5)

    class Config:
        from_attributes = True


@router.get("/questions", response_model=List[QuestionResponse])
async def get_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get all active questions for the test (student only, no correct answers)"""
    try:
        questions = db.query(Question).filter(
            Question.is_active == True
        ).order_by(Question.order_index).all()
        
        return [
            QuestionResponse(
                question_id=q.id,
                question_text=q.question_text,
                options=parse_options_to_array(q.options)
            )
            for q in questions
        ]
    except Exception as e:
        import traceback
        print(f"❌ Error in get_questions: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch questions: {str(e)}"
        )


@router.post("/start", response_model=TestStartResponse, status_code=status.HTTP_200_OK)
async def start_test(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Start a new test attempt or return existing in-progress attempt"""
    # Ensure student profile exists
    from models.student import Student
    student_profile = db.query(Student).filter(Student.user_id == current_user.id).first()
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student profile not found. Please complete your registration."
        )
    
    # Check if user has already completed a test (ONE ATTEMPT ONLY)
    completed_attempt = db.query(TestAttempt).filter(
        TestAttempt.student_id == current_user.id,
        TestAttempt.status == TestStatus.COMPLETED
    ).first()
    
    if completed_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already completed the test. Each student can attempt the test only once."
        )
    
    # Check if user has an in-progress test
    existing_attempt = db.query(TestAttempt).filter(
        TestAttempt.student_id == current_user.id,
        TestAttempt.status == TestStatus.IN_PROGRESS
    ).first()
    
    # If exists → return it (do NOT error)
    if existing_attempt:
        total_questions = db.query(Question).filter(Question.is_active == True).count()
        return {
            "test_attempt_id": existing_attempt.id,
            "status": existing_attempt.status.value,
            "started_at": existing_attempt.started_at,
            "total_questions": total_questions
        }
    
    # Get total questions count
    total_questions = db.query(Question).filter(Question.is_active == True).count()
    
    # Create new test attempt
    test_attempt = TestAttempt(
        student_id=current_user.id,
        status=TestStatus.IN_PROGRESS
    )
    
    db.add(test_attempt)
    db.commit()
    db.refresh(test_attempt)
    
    return {
        "test_attempt_id": test_attempt.id,
        "status": test_attempt.status.value,
        "started_at": test_attempt.started_at,
        "total_questions": total_questions
    }


@router.post("/submit", response_model=TestResultResponse, status_code=status.HTTP_200_OK)
async def submit_answers(
    submit_data: SubmitAnswersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Submit answers, calculate score, and save result (student only)"""
    test_attempt_id = submit_data.attempt_id
    
    # Verify test attempt belongs to current user
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == test_attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    if test_attempt.status != TestStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test attempt is not in progress"
        )
    
    # Get all active questions
    all_questions = db.query(Question).filter(
        Question.is_active == True
    ).order_by(Question.order_index).all()
    
    total_questions = len(all_questions)
    
    if len(submit_data.answers) != total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must answer all questions. Expected {total_questions}, got {len(submit_data.answers)}"
        )
    
    # Validate all questions exist and are active
    question_ids = [ans.question_id for ans in submit_data.answers]
    question_map = {q.id: q for q in all_questions}
    
    for qid in question_ids:
        if qid not in question_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {qid} is invalid or not active"
            )
    
    # Check for duplicate submissions
    existing_answers = db.query(Answer).filter(
        Answer.test_attempt_id == test_attempt_id
    ).count()
    
    if existing_answers > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answers already submitted for this attempt"
        )
    
    # Save answers
    for answer_data in submit_data.answers:
        answer = Answer(
            test_attempt_id=test_attempt_id,
            question_id=answer_data.question_id,
            answer_text=answer_data.selected_option
        )
        db.add(answer)
    
    # Calculate score
    correct_count = 0
    for answer_data in submit_data.answers:
        question = question_map[answer_data.question_id]
        if question.correct_answer and answer_data.selected_option.upper() == question.correct_answer.upper():
            correct_count += 1
    
    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0.0
    
    # Create Score record
    from models import Score
    score = Score(
        test_attempt_id=test_attempt_id,
        dimension="overall",
        score_value=percentage,
        percentile=None
    )
    db.add(score)
    
    # Update test attempt
    from datetime import datetime, timezone
    test_attempt.status = TestStatus.COMPLETED
    test_attempt.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return TestResultResponse(
        total_questions=total_questions,
        correct_answers=correct_count,
        percentage=round(percentage, 2),
        status="COMPLETED"
    )


@router.post("/{test_attempt_id}/complete", status_code=status.HTTP_200_OK)
async def complete_test(
    test_attempt_id: int,
    auto_submit: bool = Query(False, description="Skip validation for auto-submit cases (timer expiry)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Complete test and calculate scores (only when all sections are completed)
    
    Args:
        test_attempt_id: ID of the test attempt to complete
        auto_submit: If True, skip "all questions answered" validation (for timer expiry cases)
    """
    # Verify test attempt belongs to current user
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == test_attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    print(f"🔵 Complete test: attempt_id={test_attempt_id}, status={test_attempt.status}, auto_submit={auto_submit}")
    
    # Make endpoint idempotent: if already completed, return success
    if test_attempt.status == TestStatus.COMPLETED:
        print(f"✅ Test {test_attempt_id} already completed, returning success (idempotent)")
        return {
            "message": "Test already completed",
            "test_attempt_id": test_attempt_id,
            "test_id": test_attempt_id,  # Add test_id alias for frontend compatibility
            "status": "COMPLETED"
        }
    
    if test_attempt.status != TestStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test attempt is not in progress (current status: {test_attempt.status.value})"
        )
    
    # Check if all sections are completed (section-wise flow)
    active_sections = db.query(Section).filter(Section.is_active == True).order_by(Section.order_index).all()
    active_section_count = len(active_sections)
    
    if active_section_count > 0:
        # Get all section progress records for this attempt
        all_progress = db.query(SectionProgress).filter(
            SectionProgress.test_attempt_id == test_attempt_id
        ).all()
        
        # Count completed sections by matching section IDs
        completed_section_ids = {
            p.section_id for p in all_progress 
            if p.status == SectionStatus.COMPLETED
        }
        
        # Check which sections are completed
        completed_sections_list = []
        missing_sections_list = []
        for section in active_sections:
            if section.id in completed_section_ids:
                completed_sections_list.append(f"Section {section.order_index}")
            else:
                missing_sections_list.append(f"Section {section.order_index} ({section.name})")
        
        completed_count = len(completed_sections_list)
        
        print(f"🔵 Section completion check: {completed_count}/{active_section_count}")
        print(f"  Completed: {completed_sections_list}")
        print(f"  Missing: {missing_sections_list}")
        print(f"  All progress records: {[(p.section_id, p.status.value) for p in all_progress]}")
        
        if completed_count < active_section_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please complete all sections. {completed_count}/{active_section_count} sections completed. Missing: {', '.join(missing_sections_list)}"
            )
    
    # Calculate expected total questions from sections (5 sections × 7 questions = 35)
    # IMPORTANT: Always use expected_total_questions (35) for validation, NOT database count
    # This ensures validation works even if database has more questions (e.g., 40)
    expected_total_questions = TOTAL_SECTIONS * QUESTIONS_PER_SECTION  # 5 * 7 = 35
    
    # Get answered questions count
    answered_questions = db.query(Answer).filter(
        Answer.test_attempt_id == test_attempt_id
    ).count()
    
    # Get actual database count for logging
    db_total_questions = db.query(Question).filter(Question.is_active == True).count()
    
    print(f"🔵 Question check: {answered_questions}/{expected_total_questions} answered (DB has {db_total_questions} active questions, auto_submit={auto_submit})")
    
    # Validate that all expected questions are answered (35 questions)
    if answered_questions < expected_total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please answer all questions. {answered_questions}/{expected_total_questions} answered"
        )
    
    if answered_questions > expected_total_questions:
        print(f"⚠️ Warning: More answers ({answered_questions}) than expected ({expected_total_questions}), proceeding with validation")
    
    # Log if database count differs from expected (for debugging)
    if db_total_questions != expected_total_questions:
        print(f"⚠️ Info: Database has {db_total_questions} active questions, expected {expected_total_questions} (using expected for validation)")
    
    # Calculate and store scores (scores are calculated from all answers, regardless of sections)
    try:
        store_scores(db, test_attempt_id)
    except Exception as e:
        print(f"❌ Error calculating scores: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate scores"
        )
    
    # Mark test attempt as completed
    from datetime import timezone
    test_attempt.status = TestStatus.COMPLETED
    test_attempt.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(test_attempt)
    
    print(f"✅ Test {test_attempt_id} marked as COMPLETED")
    
    # Auto-create interpretation if it doesn't exist
    try:
        interpreted_result = db.query(InterpretedResult).filter(
            InterpretedResult.test_attempt_id == test_attempt_id
        ).first()
        
        if not interpreted_result:
            print(f"🔵 Auto-creating interpretation for test {test_attempt_id}")
            # Get score for interpretation
            score = db.query(Score).filter(
                Score.test_attempt_id == test_attempt_id,
                Score.dimension == "overall"
            ).first()
            
            if score:
                total_questions = expected_total_questions
                percentage = score.score_value
                correct_answers = int((percentage / 100) * total_questions) if percentage <= 100 else total_questions
                
                # Generate interpretation in background (non-blocking)
                try:
                    generate_and_save_interpretation(
                        db, test_attempt_id, total_questions, correct_answers, percentage
                    )
                    print(f"✅ Interpretation generated for test {test_attempt_id}")
                except Exception as e:
                    print(f"⚠️ Failed to generate interpretation: {e}")
                    # Don't fail the completion if interpretation generation fails
    except Exception as e:
        print(f"⚠️ Error during interpretation auto-creation: {e}")
        # Don't fail the completion if interpretation creation fails
    
    return {
        "message": "Test completed successfully",
        "test_attempt_id": test_attempt_id,
        "test_id": test_attempt_id,  # Add test_id alias for frontend compatibility
        "status": "COMPLETED"
    }


@router.get("/{test_attempt_id}/status", response_model=TestStatusResponse)
async def get_test_status(
    test_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get test attempt status (without raw scores)"""
    # Verify test attempt belongs to current user
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == test_attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    total_questions = db.query(Question).filter(Question.is_active == True).count()
    answered_questions = db.query(Answer).filter(
        Answer.test_attempt_id == test_attempt_id
    ).count()
    
    # Get completed sections by querying SectionProgress
    completed_progresses = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == test_attempt_id,
        SectionProgress.status == SectionStatus.COMPLETED
    ).all()
    
    # Get section order_index for each completed section
    completed_sections = []
    for progress in completed_progresses:
        section = db.query(Section).filter(Section.id == progress.section_id).first()
        if section:
            completed_sections.append(section.order_index)
    
    # Sort completed sections
    completed_sections = sorted(completed_sections)
    
    # Find current section (next incomplete section)
    all_sections = db.query(Section).filter(Section.is_active == True).order_by(Section.order_index).all()
    current_section = None
    for section in all_sections:
        if section.order_index not in completed_sections:
            current_section = section.order_index
            break
    
    # If all sections completed, current_section is None
    # Get total sections from database (should be 5)
    total_sections = db.query(Section).filter(Section.is_active == True).count()
    if total_sections == 0:
        total_sections = TOTAL_SECTIONS  # Fallback to constant if no sections found
    
    return {
        "test_attempt_id": test_attempt.id,
        "status": test_attempt.status.value,
        "started_at": test_attempt.started_at,
        "completed_at": test_attempt.completed_at,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "completed_sections": completed_sections,
        "current_section": current_section,
        "total_sections": total_sections
    }


@router.get("/interpretation/{test_attempt_id}", response_model=InterpretationResponse)
async def get_interpretation(
    test_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student_or_counsellor)
):
    """Get or generate AI interpretation for test attempt (Student or Counsellor)"""
    # Verify test attempt exists
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == test_attempt_id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    # If student, verify it's their attempt
    if current_user.role == UserRole.STUDENT and test_attempt.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if test_attempt.status != TestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test must be completed before interpretation"
        )
    
    # Calculate expected total questions from sections (5 sections × 7 questions = 35)
    expected_total_questions = TOTAL_SECTIONS * QUESTIONS_PER_SECTION  # 5 * 7 = 35
    
    # Check if interpretation already exists
    interpreted_result = db.query(InterpretedResult).filter(
        InterpretedResult.test_attempt_id == test_attempt_id
    ).first()
    
    # Get score data
    score = db.query(Score).filter(
        Score.test_attempt_id == test_attempt_id,
        Score.dimension == "overall"
    ).first()
    
    if not score:
        # Auto-create score if missing (shouldn't happen, but handle gracefully)
        print(f"⚠️ Score not found for test {test_attempt_id}, attempting to calculate...")
        try:
            store_scores(db, test_attempt_id)
            score = db.query(Score).filter(
                Score.test_attempt_id == test_attempt_id,
                Score.dimension == "overall"
            ).first()
        except Exception as e:
            print(f"❌ Failed to calculate score: {e}")
        
        if not score:
            # Return a default interpretation instead of 404
            print(f"⚠️ Still no score found, returning default interpretation")
            return InterpretationResponse(
                summary="Assessment results are being processed. Please check back in a moment.",
                strengths=[],
                weaknesses=[],
                career_clusters=[],
                risk_level="MEDIUM",
                readiness_status="PROCESSING",
                action_plan=["Results are being calculated. Please refresh in a moment."],
                overall_percentage=0.0,
                total_questions=expected_total_questions,
                correct_answers=0,
                is_ai_generated=False
            )
    
    # Get answered questions count
    answered_count = db.query(Answer).filter(Answer.test_attempt_id == test_attempt_id).count()
    
    # Validate that all expected questions are answered (35 questions)
    if answered_count < expected_total_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate interpretation: {answered_count}/{expected_total_questions} questions answered"
        )
    
    # Use expected total for score calculation
    # IMPORTANT: overall_percentage is calculated ONCE in scoring.py and stored in scores table
    # Do NOT recalculate here - always use score.score_value from database
    total_questions = expected_total_questions
    percentage = score.score_value  # Retrieved from scores table - single source of truth
    
    # Clamp percentage to valid range (0-100) if somehow invalid, but don't recalculate
    if percentage < 0 or percentage > 100:
        print(f"⚠️ Warning: Invalid percentage {percentage} for test {test_attempt_id}, clamping to valid range")
        percentage = max(0.0, min(100.0, percentage))
    
    # Calculate correct_answers for display purposes only (not stored, just for API response)
    correct_answers = int((percentage / 100) * total_questions) if percentage <= 100 else total_questions
    
    # Generate interpretation if not exists
    if not interpreted_result:
        try:
            interpreted_result, interpretation_data = generate_and_save_interpretation(
                db, test_attempt_id, total_questions, correct_answers, percentage
            )
            print(f"✅ Interpretation generated for test {test_attempt_id}")
        except Exception as e:
            print(f"⚠️ Failed to generate interpretation: {e}")
            # Return a processing message instead of 404
            from services.gemini_interpreter import (
                calculate_readiness_status, calculate_risk_level,
                determine_career_direction, generate_action_roadmap
            )
            from models import Section
            
            readiness_status, readiness_explanation = calculate_readiness_status(percentage)
            risk_level, risk_explanation = calculate_risk_level(readiness_status)
            
            sections = {}
            section_objs = db.query(Section).all()
            for section in section_objs:
                sections[section.order_index] = section.name
            
            section_scores_dict = {}
            scores_query = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
            for score in scores_query:
                if score.dimension.startswith("section_"):
                    section_scores_dict[score.dimension] = score.score_value
            
            career_direction, career_direction_reason = determine_career_direction(section_scores_dict, sections, percentage)
            roadmap = generate_action_roadmap(readiness_status, percentage)
            
            return InterpretationResponse(
                summary="AI interpretation is being generated. Please refresh in a moment.",
                strengths=[],
                weaknesses=[],
                career_clusters=[career_direction],
                risk_level=risk_level,
                readiness_status=readiness_status,
                action_plan=["Interpretation is being generated. Please refresh in a moment."],
                overall_percentage=round(percentage, 2),
                total_questions=total_questions,
                correct_answers=correct_answers,
                is_ai_generated=False,
                readiness_explanation=readiness_explanation,
                risk_explanation=risk_explanation,
                career_direction=career_direction,
                career_direction_reason=career_direction_reason,
                roadmap=roadmap
            )
    else:
        # Parse existing interpretation - regenerate missing fields if needed
        import json
        from services.gemini_interpreter import (
            calculate_readiness_status, calculate_risk_level,
            determine_career_direction, generate_action_roadmap,
            generate_counsellor_style_summary
        )
        from models import Section
        
        readiness_status, readiness_explanation = calculate_readiness_status(percentage)
        risk_level, risk_explanation = calculate_risk_level(readiness_status)
        
        sections = {}
        section_objs = db.query(Section).all()
        for section in section_objs:
            sections[section.order_index] = section.name
        
        section_scores_dict = {}
        scores_query = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
        for score in scores_query:
            if score.dimension.startswith("section_"):
                section_scores_dict[score.dimension] = score.score_value
        
        career_direction, career_direction_reason = determine_career_direction(section_scores_dict, sections)
        roadmap = generate_action_roadmap(readiness_status, percentage)
        
        interpretation_data = {
            "summary": interpreted_result.interpretation_text or generate_counsellor_style_summary(
                percentage, readiness_status, career_direction, total_questions, correct_answers
            ),
            "strengths": json.loads(interpreted_result.strengths) if interpreted_result.strengths else [],
            "weaknesses": json.loads(interpreted_result.areas_for_improvement) if interpreted_result.areas_for_improvement else [],
            "career_clusters": [career_direction],
            "risk_level": risk_level,
            "readiness_status": readiness_status,
            "action_plan": [
                roadmap["phase1"]["title"] + ": " + ", ".join(roadmap["phase1"]["actions"][:2]),
                roadmap["phase2"]["title"] + ": " + ", ".join(roadmap["phase2"]["actions"][:2]),
                roadmap["phase3"]["title"] + ": " + ", ".join(roadmap["phase3"]["actions"][:2])
            ],
            "readiness_explanation": readiness_explanation,
            "risk_explanation": risk_explanation,
            "career_direction": career_direction,
            "career_direction_reason": career_direction_reason,
            "roadmap": roadmap
        }
    
    is_ai_generated = False
    if interpreted_result:
        is_ai_generated = interpreted_result.is_ai_generated
    
    return InterpretationResponse(
        summary=interpretation_data.get("summary", ""),
        strengths=interpretation_data.get("strengths", []),
        weaknesses=interpretation_data.get("weaknesses", []),
        career_clusters=interpretation_data.get("career_clusters", []),
        risk_level=interpretation_data.get("risk_level", "MEDIUM"),
        readiness_status=interpretation_data.get("readiness_status", "PARTIALLY READY"),
        action_plan=interpretation_data.get("action_plan", []),
        overall_percentage=round(percentage, 2),
        total_questions=total_questions,
        correct_answers=correct_answers,
        is_ai_generated=is_ai_generated,
        readiness_explanation=interpretation_data.get("readiness_explanation", ""),
        risk_explanation=interpretation_data.get("risk_explanation", ""),
        career_direction=interpretation_data.get("career_direction", "Multi-domain Exploration"),
        career_direction_reason=interpretation_data.get("career_direction_reason", ""),
        roadmap=interpretation_data.get("roadmap", {})
    )


# ========== SECTION-WISE TEST FLOW ENDPOINTS ==========

class SectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    order_index: int
    status: Optional[str] = None  # NOT_STARTED, IN_PROGRESS, COMPLETED

    class Config:
        from_attributes = True


class SectionProgressResponse(BaseModel):
    section_id: int
    section_name: str
    status: str
    total_time_spent: int  # seconds
    is_paused: bool
    current_time: Optional[int] = None  # Current elapsed time if running

    class Config:
        from_attributes = True


class SubmitSectionRequest(BaseModel):
    attempt_id: int
    section_id: int
    answers: List[AnswerSubmit]


class SectionMetadataResponse(BaseModel):
    id: int
    name: str
    status: str  # "available", "completed", or "locked"
    question_count: int = QUESTIONS_PER_SECTION  # Fixed: QUESTIONS_PER_SECTION questions per section
    time_limit: int = 420  # Fixed: 7 minutes (420 seconds) per section
    order_index: int  # Section order (1-5)

    class Config:
        from_attributes = True


class SectionsListResponse(BaseModel):
    current_section: int
    sections: List[SectionMetadataResponse]
    can_attempt_test: bool = True  # Whether student can start a new test attempt
    completed_test_attempt_id: Optional[int] = None  # ID of completed test if exists
    
    class Config:
        from_attributes = True


@router.get("/sections", response_model=SectionsListResponse)
async def get_sections(
    attempt_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get all active sections with status for current student's test attempt"""
    # Check if student has already completed a test (ONE ATTEMPT ONLY)
    # Query for ANY completed attempt for this student
    completed_attempt = db.query(TestAttempt).filter(
        TestAttempt.student_id == current_user.id,
        TestAttempt.status == TestStatus.COMPLETED
    ).order_by(TestAttempt.completed_at.desc()).first()  # Get most recent completed attempt
    
    can_attempt_test = completed_attempt is None
    completed_test_attempt_id = completed_attempt.id if completed_attempt else None
    
    # Debug logging
    print(f"🔵 get_sections for user {current_user.id}: can_attempt_test={can_attempt_test}, completed_test_attempt_id={completed_test_attempt_id}")
    if completed_attempt:
        print(f"   Found completed attempt: ID={completed_attempt.id}, completed_at={completed_attempt.completed_at}")
    
    # Find current test attempt for this student (in progress or completed)
    if attempt_id:
        test_attempt = db.query(TestAttempt).filter(
            TestAttempt.id == attempt_id,
            TestAttempt.student_id == current_user.id,
            TestAttempt.status == TestStatus.IN_PROGRESS
        ).first()
    else:
        test_attempt = db.query(TestAttempt).filter(
            TestAttempt.student_id == current_user.id,
            TestAttempt.status == TestStatus.IN_PROGRESS
        ).first()
    
    # FIXED: Define all 5 sections - ALWAYS return all 5 sections
    # This ensures sections are returned regardless of database state
    sections_config = [
        {
            "order_index": 1,
            "name": "Section 1: Intelligence Test (Cognitive Reasoning)",
            "description": "Logical Reasoning, Numerical Reasoning, Verbal Reasoning, Abstract Reasoning"
        },
        {
            "order_index": 2,
            "name": "Section 2: Aptitude Test",
            "description": "Numerical Aptitude, Logical Aptitude, Verbal Aptitude, Spatial/Mechanical Aptitude"
        },
        {
            "order_index": 3,
            "name": "Section 3: Study Habits",
            "description": "Concentration, Consistency, Time Management, Exam Preparedness, Self-discipline"
        },
        {
            "order_index": 4,
            "name": "Section 4: Learning Style",
            "description": "Visual, Auditory, Reading/Writing, Kinesthetic"
        },
        {
            "order_index": 5,
            "name": "Section 5: Career Interest (RIASEC)",
            "description": "Realistic, Investigative, Artistic, Social, Enterprising, Conventional"
        }
    ]
    
    # Get sections from database, but ensure we have all 5
    db_sections = db.query(Section).filter(
        Section.is_active == True
    ).order_by(Section.order_index).all()
    
    # Create a map of order_index -> Section for quick lookup
    db_sections_map = {s.order_index: s for s in db_sections}
    
    # Build all_sections list - always 5 sections
    all_sections = []
    print(f"🔵 Building sections: DB has {len(db_sections)} sections, config has {len(sections_config)} sections")
    for config in sections_config:
        order_idx = config["order_index"]
        if order_idx in db_sections_map:
            # Use database section if it exists
            print(f"  ✅ Using DB section {order_idx}: {db_sections_map[order_idx].name}")
            all_sections.append(db_sections_map[order_idx])
        else:
            # Create a temporary section object from config if not in DB
            # This ensures we always return 5 sections
            print(f"  ⚠️ Creating temp section {order_idx}: {config['name']}")
            temp_section = type('Section', (), {
                'id': order_idx,  # Use order_index as temporary ID
                'name': config["name"],
                'description': config["description"],
                'order_index': order_idx,
                'is_active': True
            })()
            all_sections.append(temp_section)
    
    print(f"🔵 Total sections built: {len(all_sections)}")
    
    # Determine current section based on progress
    current_section_index = 0  # 0 means no section started yet
    
    if test_attempt:
        # Find the current section based on progress
        # Look for in-progress sections first
        in_progress_progress = db.query(SectionProgress).filter(
            SectionProgress.test_attempt_id == test_attempt.id,
            SectionProgress.status == SectionStatus.IN_PROGRESS
        ).all()
        
        if in_progress_progress:
            # Get the section order_index for the in-progress section
            for progress in in_progress_progress:
                section = db.query(Section).filter(Section.id == progress.section_id).first()
                if section:
                    current_section_index = section.order_index
                    break
        else:
            # Find the highest completed section
            completed_progress = db.query(SectionProgress).filter(
                SectionProgress.test_attempt_id == test_attempt.id,
                SectionProgress.status == SectionStatus.COMPLETED
            ).all()
            
            if completed_progress:
                # Get order_index for all completed sections
                completed_order_indices = []
                for progress in completed_progress:
                    section = db.query(Section).filter(Section.id == progress.section_id).first()
                    if section:
                        completed_order_indices.append(section.order_index)
                
                if completed_order_indices:
                    highest_completed = max(completed_order_indices)
                    if highest_completed < 5:  # If not all sections completed
                        current_section_index = highest_completed + 1
                    else:
                        current_section_index = 5  # All sections completed
                else:
                    # No valid sections found - default to Section 1
                    current_section_index = 1
            else:
                # No progress at all - Section 1 should be available
                current_section_index = 1
    
    # If no attempt or current_section is 0, default to Section 1
    if not test_attempt or current_section_index == 0:
        current_section_index = 1
    
    sections_result = []
    print(f"🔵 Processing {len(all_sections)} sections for response")
    
    for section in all_sections:
        try:
            print(f"  Processing section {section.order_index}: {section.name}")
            # CRITICAL: Section 1 is NEVER locked
            if section.order_index == 1:
                if not test_attempt:
                    # No attempt - Section 1 is always available
                    section_status = "available"
                else:
                    # Check Section 1 progress - need to find section by order_index if temp section
                    section1_id = section.id if (hasattr(section, 'id') and isinstance(section.id, int) and section.id > 0) else None
                    
                    if section1_id:
                        # Real database section - query by ID
                        section1_progress = db.query(SectionProgress).filter(
                            SectionProgress.test_attempt_id == test_attempt.id,
                            SectionProgress.section_id == section1_id
                        ).first()
                    else:
                        # Temp section - find by order_index
                        db_section1 = db.query(Section).filter(Section.order_index == 1).first()
                        if db_section1:
                            section1_progress = db.query(SectionProgress).filter(
                                SectionProgress.test_attempt_id == test_attempt.id,
                                SectionProgress.section_id == db_section1.id
                            ).first()
                        else:
                            section1_progress = None
                    
                    if section1_progress and section1_progress.status == SectionStatus.COMPLETED:
                        section_status = "completed"
                    elif current_section_index == 1:
                        # Section 1 is current - available
                        section_status = "available"
                    else:
                        # Section 1 should be available if not completed
                        section_status = "available"
            else:
                # Sections 2-5: Apply locking rules based on current_section
                if not test_attempt or current_section_index == 0 or current_section_index == 1:
                    # No attempt or Section 1 is current - all sections 2-5 are locked
                    section_status = "locked"
                else:
                    # Check progress for this section - handle both DB and temp sections
                    section_id = section.id if (hasattr(section, 'id') and isinstance(section.id, int) and section.id > 0) else None
                    
                    if section_id:
                        # Real database section - query by ID
                        progress = db.query(SectionProgress).filter(
                            SectionProgress.test_attempt_id == test_attempt.id,
                            SectionProgress.section_id == section_id
                        ).first()
                    else:
                        # Temp section - find by order_index
                        db_section = db.query(Section).filter(Section.order_index == section.order_index).first()
                        if db_section:
                            progress = db.query(SectionProgress).filter(
                                SectionProgress.test_attempt_id == test_attempt.id,
                                SectionProgress.section_id == db_section.id
                            ).first()
                        else:
                            progress = None
                    
                    if section.order_index < current_section_index:
                        # Section is before current - should be completed
                        section_status = "completed"
                    elif section.order_index == current_section_index:
                        # This is the current section
                        if progress and progress.status == SectionStatus.COMPLETED:
                            section_status = "completed"
                        else:
                            section_status = "available"
                    else:
                        # Section is after current - check if previous sections are completed
                        prev_sections_completed = True
                        for prev_section in all_sections:
                            if prev_section.order_index < section.order_index:
                                prev_section_id = prev_section.id if (hasattr(prev_section, 'id') and isinstance(prev_section.id, int) and prev_section.id > 0) else None
                                
                                if prev_section_id:
                                    prev_progress = db.query(SectionProgress).filter(
                                        SectionProgress.test_attempt_id == test_attempt.id,
                                        SectionProgress.section_id == prev_section_id,
                                        SectionProgress.status == SectionStatus.COMPLETED
                                    ).first()
                                else:
                                    # Temp section - find by order_index
                                    db_prev_section = db.query(Section).filter(Section.order_index == prev_section.order_index).first()
                                    if db_prev_section:
                                        prev_progress = db.query(SectionProgress).filter(
                                            SectionProgress.test_attempt_id == test_attempt.id,
                                            SectionProgress.section_id == db_prev_section.id,
                                            SectionProgress.status == SectionStatus.COMPLETED
                                        ).first()
                                    else:
                                        prev_progress = None
                                
                                if not prev_progress:
                                    prev_sections_completed = False
                                    break
                        
                        if prev_sections_completed:
                            section_status = "available"
                        else:
                            section_status = "locked"
            
            # Question count - default to 7, don't query if section not in DB
            # Question availability is checked ONLY when section starts, not while listing
            question_count = QUESTIONS_PER_SECTION  # Fixed: QUESTIONS_PER_SECTION questions per section
            
            # Only query question count if section exists in database (has real ID from DB)
            if hasattr(section, 'id') and isinstance(section.id, int) and section.id > 0:
                try:
                    # Check if this is a real database section (not a temp object)
                    db_section_check = db.query(Section).filter(Section.id == section.id).first()
                    if db_section_check:
                        actual_count = db.query(Question).filter(
                            Question.section_id == section.id,
                            Question.is_active == True
                        ).count()
                        # Use actual count if available, but default to 10 if 0
                        if actual_count > 0:
                            question_count = actual_count
                except:
                    # If query fails, use default 10
                    pass
            
            # Use section.id if it's a real database section, otherwise use order_index
            section_id = section.id if (hasattr(section, 'id') and isinstance(section.id, int) and section.id > 0) else section.order_index
            
            sections_result.append(SectionMetadataResponse(
                id=section_id,
                name=section.name,
                status=section_status,
                question_count=question_count,
                time_limit=420,  # Fixed: 7 minutes per section
                order_index=section.order_index
            ))
            print(f"  ✅ Added section {section.order_index} to result")
        except Exception as e:
            print(f"  ❌ ERROR processing section {section.order_index}: {e}")
            import traceback
            traceback.print_exc()
    
    # Debug: Ensure we always return exactly 5 sections
    print(f"🔵 Final sections_result count: {len(sections_result)}")
    if len(sections_result) != 5:
        print(f"⚠️ WARNING: Expected 5 sections but got {len(sections_result)}")
        print(f"   Sections order_index: {[s.order_index for s in sections_result]}")
    else:
        print(f"✅ Successfully returning all 5 sections")
    
    response = SectionsListResponse(
        current_section=current_section_index,
        sections=sections_result,
        can_attempt_test=can_attempt_test,
        completed_test_attempt_id=completed_test_attempt_id
    )
    print(f"🔵 Response sections count: {len(response.sections)}")
    print(f"🔵 Response can_attempt_test: {response.can_attempt_test}, completed_test_attempt_id: {response.completed_test_attempt_id}")
    return response


@router.get("/sections/{section_id}/questions", response_model=List[QuestionResponse])
async def get_section_questions(
    section_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get questions for a specific section (only if section is unlocked)"""
    # Verify test attempt belongs to user
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    # Verify section exists - try by ID first, then by order_index (for sections 4-5 that might use order_index as ID)
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        # Try finding by order_index if section_id matches an order_index (for temp sections)
        if 1 <= section_id <= 5:
            section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    # Check if section is unlocked (previous sections must be completed)
    if section.order_index > 1:
        previous_sections = db.query(Section).filter(
            Section.order_index < section.order_index,
            Section.is_active == True
        ).order_by(Section.order_index).all()
        
        for prev_section in previous_sections:
            prev_progress = db.query(SectionProgress).filter(
                SectionProgress.test_attempt_id == attempt_id,
                SectionProgress.section_id == prev_section.id,
                SectionProgress.status == SectionStatus.COMPLETED
            ).first()
            
            if not prev_progress:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Please complete {prev_section.name} first"
                )
    
    # Get questions for this section
    questions = db.query(Question).filter(
        Question.section_id == section_id,
        Question.is_active == True
    ).order_by(Question.order_index).all()
    
    # CRITICAL: Validate exactly QUESTIONS_PER_SECTION questions per section
    if len(questions) != QUESTIONS_PER_SECTION:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Section must have exactly {QUESTIONS_PER_SECTION} questions. Found {len(questions)} questions."
        )
    
    return [
        QuestionResponse(
            question_id=q.id,
            question_text=q.question_text,
            options=parse_options_to_array(q.options)
        )
        for q in questions
    ]


@router.post("/sections/{section_id}/start", response_model=SectionProgressResponse)
async def start_section(
    section_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Start a section (initialize progress and timer)"""
    # Verify test attempt
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    # Verify section exists - try by ID first, then by order_index (for sections 4-5 that might use order_index as ID)
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        # Try finding by order_index if section_id matches an order_index (for temp sections)
        if 1 <= section_id <= 5:
            section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    # Check if section is unlocked (same logic as get_section_questions)
    if section.order_index > 1:
        previous_sections = db.query(Section).filter(
            Section.order_index < section.order_index,
            Section.is_active == True
        ).order_by(Section.order_index).all()
        
        for prev_section in previous_sections:
            prev_progress = db.query(SectionProgress).filter(
                SectionProgress.test_attempt_id == attempt_id,
                SectionProgress.section_id == prev_section.id,
                SectionProgress.status == SectionStatus.COMPLETED
            ).first()
            
            if not prev_progress:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Please complete {prev_section.name} first"
                )
    
    # Get or create section progress
    # CRITICAL: Use actual database section ID, not the parameter (which might be order_index)
    progress = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == attempt_id,
        SectionProgress.section_id == section.id  # Use actual database section ID
    ).first()
    
    if not progress:
        # Create new progress
        progress = SectionProgress(
            test_attempt_id=attempt_id,
            section_id=section.id,  # Use actual database section ID
            status=SectionStatus.IN_PROGRESS,
            section_start_time=datetime.now()
        )
        db.add(progress)
    else:
        # Resume if paused, or continue if already in progress
        if progress.status == SectionStatus.NOT_STARTED:
            progress.status = SectionStatus.IN_PROGRESS
            progress.section_start_time = datetime.now()
        elif progress.status == SectionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section already completed"
            )
        elif progress.paused_at:
            # Resume from pause
            paused_duration = (datetime.now() - progress.paused_at).total_seconds()
            progress.total_time_spent += int(paused_duration)
            progress.paused_at = None
            progress.status = SectionStatus.IN_PROGRESS
            if not progress.section_start_time:
                progress.section_start_time = datetime.now()
    
    db.commit()
    db.refresh(progress)
    
    return SectionProgressResponse(
        section_id=section.id,
        section_name=section.name,
        status=progress.status.value,
        total_time_spent=progress.total_time_spent,
        is_paused=progress.paused_at is not None,
        current_time=progress.total_time_spent
    )


@router.post("/sections/{section_id}/pause")
async def pause_section(
    section_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Pause section timer"""
    # First, find the section by ID or order_index
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section and 1 <= section_id <= 5:
        section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    # Use actual database section ID to find progress
    progress = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == attempt_id,
        SectionProgress.section_id == section.id  # Use actual database section ID
    ).first()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section progress not found"
        )
    
    if progress.status != SectionStatus.IN_PROGRESS or progress.paused_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section is not running"
        )
    
    # Calculate time spent since start
    if progress.section_start_time:
        elapsed = (datetime.now() - progress.section_start_time).total_seconds()
        progress.total_time_spent += int(elapsed)
        progress.section_start_time = None
    
    progress.paused_at = datetime.now()
    db.commit()
    
    return {"message": "Section paused", "total_time_spent": progress.total_time_spent}


@router.post("/sections/{section_id}/resume")
async def resume_section(
    section_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Resume section timer"""
    # First, find the section by ID or order_index
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section and 1 <= section_id <= 5:
        section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    # Use actual database section ID to find progress
    progress = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == attempt_id,
        SectionProgress.section_id == section.id  # Use actual database section ID
    ).first()
    
    if not progress or not progress.paused_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section is not paused"
        )
    
    # Resume timer
    progress.section_start_time = datetime.now()
    progress.paused_at = None
    progress.status = SectionStatus.IN_PROGRESS
    db.commit()
    
    return {"message": "Section resumed", "total_time_spent": progress.total_time_spent}


@router.get("/sections/{section_id}/timer", response_model=SectionProgressResponse)
async def get_section_timer(
    section_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get current timer status for a section (backend-driven)"""
    # First, find the section by ID or order_index
    # This is critical because section_id might be order_index for sections 4-5
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section and 1 <= section_id <= 5:
        section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        print(f"⚠️ Timer: Section not found - section_id={section_id}, attempt_id={attempt_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    print(f"🔵 Timer: Found section - id={section.id}, order_index={section.order_index}, name={section.name}")
    
    # Now use the actual database section ID to find progress
    # Progress is always stored with the actual database section ID
    progress = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == attempt_id,
        SectionProgress.section_id == section.id  # Use actual database section ID
    ).first()
    
    if not progress:
        print(f"⚠️ Timer: Progress not found - section_id={section.id} (db), order_index={section.order_index}, attempt_id={attempt_id}")
        # If progress doesn't exist, return a default response (section not started yet)
        return SectionProgressResponse(
            section_id=section.id,
            section_name=section.name,
            status=SectionStatus.NOT_STARTED.value,
            total_time_spent=0,
            is_paused=False,
            current_time=0
        )
    
    # Calculate current time if running
    # CRITICAL: Enforce 7-minute (420 seconds) limit per section
    SECTION_TIME_LIMIT = 420  # 7 minutes in seconds
    
    current_time = progress.total_time_spent
    if progress.section_start_time and not progress.paused_at:
        elapsed = (datetime.now() - progress.section_start_time).total_seconds()
        current_time = progress.total_time_spent + int(elapsed)
        
        # Enforce time limit - auto-complete if exceeded
        if current_time >= SECTION_TIME_LIMIT:
            # Time limit exceeded, mark section as completed
            progress.total_time_spent = SECTION_TIME_LIMIT
            progress.section_start_time = None
            progress.status = SectionStatus.COMPLETED
            progress.paused_at = None
            db.commit()
            current_time = SECTION_TIME_LIMIT
    
    # Cap current_time at limit
    current_time = min(current_time, SECTION_TIME_LIMIT)
    
    return SectionProgressResponse(
        section_id=section.id,
        section_name=section.name,
        status=progress.status.value,
        total_time_spent=progress.total_time_spent,
        is_paused=progress.paused_at is not None,
        current_time=current_time
    )


@router.post("/sections/{section_id}/submit", status_code=status.HTTP_200_OK)
async def submit_section(
    section_id: int,
    submit_data: SubmitSectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Submit answers for a section"""
    if submit_data.section_id != section_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section ID mismatch"
        )
    
    # Verify test attempt
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == submit_data.attempt_id,
        TestAttempt.student_id == current_user.id
    ).first()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    # Verify section - try by ID first, then by order_index (for sections 4-5 that might use order_index as ID)
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        # Try finding by order_index if section_id matches an order_index (for temp sections)
        if 1 <= section_id <= 5:
            section = db.query(Section).filter(Section.order_index == section_id).first()
    
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found (ID: {section_id})"
        )
    
    # Get section questions - use actual database section ID
    section_questions = db.query(Question).filter(
        Question.section_id == section.id,  # Use actual database section ID
        Question.is_active == True
    ).order_by(Question.order_index).all()
    
    # CRITICAL: Validate exactly QUESTIONS_PER_SECTION questions per section
    if len(section_questions) != QUESTIONS_PER_SECTION:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Section must have exactly {QUESTIONS_PER_SECTION} questions. Found {len(section_questions)} questions."
        )
    
    if len(submit_data.answers) != len(section_questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must answer all questions in section. Expected {len(section_questions)}, got {len(submit_data.answers)}"
        )
    
    # Check if section already submitted - use actual database section ID
    progress = db.query(SectionProgress).filter(
        SectionProgress.test_attempt_id == submit_data.attempt_id,
        SectionProgress.section_id == section.id  # Use actual database section ID
    ).first()
    
    if progress and progress.status == SectionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section already submitted"
        )
    
    # Check for duplicate answers for this section - use actual database section ID
    existing_answers = db.query(Answer).join(Question).filter(
        Answer.test_attempt_id == submit_data.attempt_id,
        Question.section_id == section.id  # Use actual database section ID
    ).count()
    
    if existing_answers > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answers already submitted for this section"
        )
    
    # Save answers
    question_map = {q.id: q for q in section_questions}
    for answer_data in submit_data.answers:
        if answer_data.question_id not in question_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {answer_data.question_id} does not belong to this section"
            )
        
        answer = Answer(
            test_attempt_id=submit_data.attempt_id,
            question_id=answer_data.question_id,
            answer_text=answer_data.selected_option
        )
        db.add(answer)
    
    # CRITICAL: Enforce 7-minute (420 seconds) limit per section
    SECTION_TIME_LIMIT = 420  # 7 minutes in seconds
    
    # Update section progress - use actual database section ID
    if not progress:
        progress = SectionProgress(
            test_attempt_id=submit_data.attempt_id,
            section_id=section.id,  # Use actual database section ID
            status=SectionStatus.COMPLETED,
            total_time_spent=0
        )
        db.add(progress)
        print(f"🔵 Created new progress for section {section.order_index} (ID: {section.id})")
    else:
        # Finalize timer
        if progress.section_start_time and not progress.paused_at:
            elapsed = (datetime.now() - progress.section_start_time).total_seconds()
            progress.total_time_spent += int(elapsed)
            progress.section_start_time = None
        
        # Cap time spent at limit
        progress.total_time_spent = min(progress.total_time_spent, SECTION_TIME_LIMIT)
        progress.status = SectionStatus.COMPLETED
        progress.paused_at = None
        print(f"🔵 Updated progress for section {section.order_index} (ID: {section.id}) to COMPLETED")
    
    db.commit()
    db.refresh(progress)
    print(f"✅ Section {section.order_index} marked as COMPLETED (progress ID: {progress.id}, section_id: {progress.section_id})")
    
    return {
        "message": "Section submitted successfully",
        "section_id": section_id,
        "next_section_available": section.order_index < db.query(Section).filter(Section.is_active == True).count()
    }

