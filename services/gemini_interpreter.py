from sqlalchemy.orm import Session
from typing import Dict, Optional, Tuple
import json
from models import Score, InterpretedResult, TestAttempt, Section


def calculate_readiness_status(percentage: float) -> Tuple[str, str]:
    """Calculate readiness status and explanation based on score"""
    if percentage < 40:
        return (
            "NOT READY",
            "The student is currently in an exploration stage. This means it is too early to finalize a career decision."
        )
    elif percentage < 60:
        return (
            "PARTIALLY READY",
            "The student has begun developing career-related strengths but needs further clarity before committing."
        )
    else:
        return (
            "READY",
            "The student shows sufficient clarity and readiness to start planning a career direction."
        )


def calculate_risk_level(readiness_status: str) -> Tuple[str, str]:
    """Calculate risk level and explanation based on readiness"""
    if readiness_status == "NOT READY":
        return (
            "HIGH",
            "Making a career decision at this stage may increase the chances of course changes or loss of interest later. This is decision risk, not failure risk - it means the student needs more time to explore before committing."
        )
    elif readiness_status == "PARTIALLY READY":
        return (
            "MEDIUM",
            "With guidance and preparation, career decisions can become more reliable over time. Early career locking may cause dissatisfaction if interests change. This is decision risk, not failure risk - it means the student should continue exploring before finalizing."
        )
    else:
        return (
            "LOW",
            "The student is well prepared to make informed career decisions. This is decision risk, not failure risk - it means the student has developed sufficient clarity to explore career options with confidence."
        )


def determine_career_direction(section_scores: Dict[str, float], sections: Dict[int, str], overall_percentage: float = 0.0) -> Tuple[str, str]:
    """Determine career direction based on strongest section scores with detailed reasoning"""
    if not section_scores:
        return (
            "Multi-domain Exploration",
            "The assessment shows balanced performance across areas. It's recommended to explore multiple career domains before specializing."
        )
    
    section_names = {
        1: "Logical Reasoning",
        2: "Numerical Ability",
        3: "Verbal Ability",
        4: "Learning Style",
        5: "Interest Areas"
    }
    
    section_percentages = {}
    for dim, score in section_scores.items():
        if dim.startswith("section_"):
            try:
                section_num = int(dim.split("_")[1])
                section_percentages[section_num] = score
            except (ValueError, IndexError):
                continue
    
    if not section_percentages:
        return (
            "Multi-domain Exploration",
            "The assessment shows balanced performance across areas. It's recommended to explore multiple career domains before specializing."
        )
    
    sorted_sections = sorted(section_percentages.items(), key=lambda x: x[1], reverse=True)
    max_section = sorted_sections[0]
    second_max = sorted_sections[1] if len(sorted_sections) > 1 else None
    third_max = sorted_sections[2] if len(sorted_sections) > 2 else None
    
    # Find weakest section
    min_section = sorted_sections[-1] if sorted_sections else None
    
    max_section_num, max_score = max_section
    max_section_name = section_names.get(max_section_num, f"Section {max_section_num}")
    
    # Build explanation with section-wise analysis
    strength_text = f"Your strongest area is {max_section_name}"
    if second_max:
        second_section_num, second_score = second_max
        second_section_name = section_names.get(second_section_num, f"Section {second_section_num}")
        strength_text += f", followed by {second_section_name}"
    if min_section:
        min_section_num, min_score = min_section
        min_section_name = section_names.get(min_section_num, f"Section {min_section_num}")
        weakness_text = f"Areas needing development include {min_section_name}"
    else:
        weakness_text = "Some areas need further development"
    
    # If overall score < 60%, show primary + secondary exploration (no single-domain dominance)
    if overall_percentage < 60:
        if second_max:
            second_section_num, second_score = second_max
            second_section_name = section_names.get(second_section_num, f"Section {second_section_num}")
            
            # Map sections to domains
            domain_map = {
                1: "Technology/Engineering",
                2: "Technology/Engineering",
                3: "Management/Commerce",
                4: "Creative/Design",
                5: "Creative/Design"
            }
            
            primary_domain = domain_map.get(max_section_num, "General")
            secondary_domain = domain_map.get(second_section_num, "General")
            
            if primary_domain == secondary_domain:
                return (
                    f"{primary_domain} (Primary) + Multi-domain Exploration (Secondary)",
                    f"{strength_text}. {weakness_text}. This domain fits because your assessment shows stronger performance in analytical and logical areas. However, you should NOT finalize a career decision yet. You are still in the exploration phase and need to test your interests through courses, projects, or internships before committing. Continue exploring multiple domains to ensure you make an informed choice later."
                )
            else:
                return (
                    f"{primary_domain} (Primary) + {secondary_domain} (Secondary)",
                    f"{strength_text}. {weakness_text}. Your assessment indicates primary alignment with {primary_domain.lower()} (strongest in {max_section_name}) and secondary interest in {secondary_domain.lower()} (strong in {second_section_name}). This combination suggests you should explore both domains. However, you should NOT finalize a career decision yet. Test your interests in both areas through practical experience, courses, or projects before committing. This balanced exploration will help you make a more informed decision later."
                )
        else:
            return (
                "Multi-domain Exploration",
                f"{strength_text}. {weakness_text}. While you show some strengths, you are still in the exploration phase. You should NOT finalize a career decision yet. Take time to build awareness and skills across different fields, test your interests through various activities, and work with a counsellor to understand your options better before specializing."
            )
    
    # For scores >= 60%, can show single domain if clear dominance
    if max_section_num in [1, 2] and (not second_max or second_max[0] in [1, 2]):
        return (
            "Technology / Engineering",
            f"{strength_text}, indicating stronger logical and problem-solving abilities. {weakness_text}. This domain fits because your assessment shows strong analytical thinking and numerical skills. You can begin exploring specific career paths in this area, but continue testing your interests through courses or projects before making a final decision. Work with a counsellor to refine your options."
        )
    elif max_section_num in [2, 3] and (not second_max or second_max[0] in [2, 3]):
        return (
            "Management / Commerce",
            f"{strength_text}, showing communication ability and interest in people-oriented roles. {weakness_text}. This domain fits because your assessment indicates strong analytical thinking combined with effective communication skills. You can begin exploring specific career paths in this area, but continue testing your interests through practical experience before making a final decision. Work with a counsellor to refine your options."
        )
    elif max_section_num in [4, 5] and (not second_max or second_max[0] in [4, 5]):
        return (
            "Creative / Design",
            f"{strength_text}, reflecting creative thinking, imagination, and interest-driven learning. {weakness_text}. This domain fits because your assessment shows strong creative and interest-based abilities. You can begin exploring specific career paths in this area, but continue testing your interests through projects or creative work before making a final decision. Work with a counsellor to refine your options."
        )
    else:
        return (
            "Multi-domain Exploration",
            f"{strength_text}. {weakness_text}. This suggests balanced abilities and the need to explore multiple fields. You should NOT finalize a career decision yet. Continue exploring different domains, testing your interests, and building skills across various areas before specializing."
        )


def generate_action_roadmap(readiness_status: str, percentage: float) -> Dict:
    """Generate 3-phase action roadmap based on readiness"""
    roadmap = {
        "phase1": {
            "duration": "0-3 Months",
            "title": "Foundation",
            "description": "This phase is meant for self-discovery and strengthening basic aptitude. No career decision should be taken yet.",
            "actions": []
        },
        "phase2": {
            "duration": "3-6 Months",
            "title": "Skill Build",
            "description": "This phase focuses on building skills in potential areas and testing interests through courses or practice.",
            "actions": []
        },
        "phase3": {
            "duration": "6-12 Months",
            "title": "Decision",
            "description": "This phase helps finalize career direction and prepare for exams, courses, or skill tracks.",
            "actions": []
        }
    }
    
    if readiness_status == "NOT READY" or percentage < 40:
        roadmap["phase1"]["description"] = "This phase is meant for self-discovery and strengthening basic aptitude. No career decision should be taken yet. Strong warning: Making career decisions now may lead to dissatisfaction later."
        roadmap["phase1"]["actions"] = [
            "Focus on aptitude improvement through practice and learning",
            "Attend career awareness sessions and counselling",
            "Explore different career domains without pressure to decide",
            "Build foundational skills in areas of interest",
            "Do NOT commit to any career path yet"
        ]
        roadmap["phase2"]["description"] = "This phase focuses on building skills in potential areas and testing interests through courses or practice. Continue exploration - no irreversible decisions."
        roadmap["phase2"]["actions"] = [
            "Continue skill development in identified weak areas",
            "Take entry-level courses or workshops in areas of interest",
            "Engage in mini projects or practical exercises",
            "Regular counselling sessions to track progress",
            "Test interests through various activities"
        ]
        roadmap["phase3"]["description"] = "This phase helps finalize career direction and prepare for exams, courses, or skill tracks. Only after 12+ months of exploration."
        roadmap["phase3"]["actions"] = [
            "Begin shortlisting 2-3 career domains based on progress",
            "Consider stream or course selection aligned with interests",
            "Start exam preparation or skill certification if applicable",
            "Finalize career direction with counsellor guidance"
        ]
    elif readiness_status == "PARTIALLY READY" or (percentage >= 40 and percentage < 60):
        roadmap["phase1"]["description"] = "This phase is meant for self-discovery and strengthening basic aptitude. Guided exploration only - no career decisions yet."
        roadmap["phase1"]["actions"] = [
            "Strengthen areas showing potential",
            "Attend career counselling to explore options",
            "Build awareness of career paths in strong areas",
            "No need to finalize career choice yet",
            "Warning: Making decisions now without exploration may lead to course dissatisfaction"
        ]
        roadmap["phase2"]["description"] = "This phase focuses on building skills in potential areas and testing interests through courses or practice. Limited shortlisting only."
        roadmap["phase2"]["actions"] = [
            "Focus on skill building in identified areas",
            "Take relevant entry-level courses",
            "Engage in practical projects or internships",
            "Continue career exploration with guidance",
            "Test interests before committing"
        ]
        roadmap["phase3"]["description"] = "This phase helps finalize career direction and prepare for exams, courses, or skill tracks. After 6-12 months of preparation."
        roadmap["phase3"]["actions"] = [
            "Shortlist 2-3 career domains based on strengths",
            "Select appropriate stream or course",
            "Begin exam or skill preparation",
            "Make informed career decision with support"
        ]
    else:
        roadmap["phase1"]["description"] = "This phase is meant for self-discovery and strengthening basic aptitude. Focused preparation allowed."
        roadmap["phase1"]["actions"] = [
            "Build on existing strengths",
            "Attend career counselling for focused guidance",
            "Explore specific career paths in strong domains",
            "Begin narrowing down options"
        ]
        roadmap["phase2"]["description"] = "This phase focuses on building skills in potential areas and testing interests through courses or practice."
        roadmap["phase2"]["actions"] = [
            "Take advanced courses in chosen domains",
            "Engage in relevant projects or internships",
            "Build specialized skills",
            "Work with counsellor to refine choices"
        ]
        roadmap["phase3"]["description"] = "This phase helps finalize career direction and prepare for exams, courses, or skill tracks."
        roadmap["phase3"]["actions"] = [
            "Finalize career direction",
            "Select appropriate stream or course",
            "Begin exam preparation or skill certification",
            "Take concrete steps toward chosen career path"
        ]
    
    return roadmap


def generate_counsellor_style_summary(
    percentage: float,
    readiness_status: str,
    career_direction: str,
    total_questions: int,
    correct_answers: int
) -> str:
    """Generate counsellor-style summary with clear stage, meaning, warnings, and next steps"""
    
    if readiness_status == "NOT READY":
        return (
            f"Based on the assessment, the student is currently in an exploration phase. "
            f"The score reflects developing aptitude across multiple areas without strong specialization yet. "
            f"This stage is common and healthy, and the focus should now be on awareness, skill building, and gradual decision-making rather than immediate career finalization. "
            f"The student should NOT finalize a career decision at this stage. Instead, they should focus on self-discovery, attend career awareness sessions, explore different domains, and work with a career counsellor. "
            f"With continued exploration and skill building over the next 12-18 months, the student will be better positioned to make an informed career decision."
        )
    elif readiness_status == "PARTIALLY READY":
        return (
            f"Based on the assessment, the student is in a preparation stage. "
            f"The score shows developing career-related strengths in certain areas while other areas need further development. "
            f"This balanced development is actually ideal at this stage - the student is building a foundation while identifying natural strengths. "
            f"The student should NOT finalize a career choice immediately. Making a career decision now without further exploration may lead to course dissatisfaction or switching later. "
            f"The focus should be on continuing to build skills, attending career counselling, taking relevant courses, and testing interests through practical projects. "
            f"With continued effort over the next 6-12 months, the student will be well-positioned to make an informed career decision."
        )
    else:
        return (
            f"Based on the assessment, the student is in a ready stage for career planning. "
            f"The score shows good readiness with strong aptitude in certain areas, particularly those aligned with {career_direction.lower()} domains. "
            f"The student has clear strengths to build upon and has developed skills that will be valuable in their future career. "
            f"While the student can begin exploring specific career paths, they should NOT rush into finalizing a career choice without proper exploration and testing of interests. "
            f"The focus should be on working with a career counsellor to refine options, taking relevant courses to build specialized skills, and testing interests through projects or internships. "
            f"Over the next 3-6 months, the student can begin making career decisions and taking concrete steps toward their chosen path."
        )


def generate_gemini_interpretation(
    total_questions: int,
    correct_answers: int,
    percentage: float,
    category_scores: Optional[Dict] = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """Generate interpretation using Gemini AI via gemini_service"""
    from services.gemini_service import generate_interpretation
    
    readiness_status, _ = calculate_readiness_status(percentage)
    
    context = {
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "percentage": percentage,
        "readiness_status": readiness_status,
        "category_scores": category_scores
    }
    
    interpretation, error = generate_interpretation(context)
    
    if error:
        print(f"⚠️ Gemini interpretation failed: {error}")
        return None, error
    
    return interpretation, None


def generate_fallback_interpretation(
    db: Session,
    test_attempt_id: int,
    total_questions: int,
    correct_answers: int,
    percentage: float,
    section_scores: Dict[str, float]
) -> Dict:
    """Generate comprehensive rule-based fallback interpretation"""
    
    readiness_status, readiness_explanation = calculate_readiness_status(percentage)
    risk_level, risk_explanation = calculate_risk_level(readiness_status)
    
    sections = {}
    section_objs = db.query(Section).all()
    for section in section_objs:
        sections[section.order_index] = section.name
    
    career_direction, career_direction_reason = determine_career_direction(section_scores, sections)
    roadmap = generate_action_roadmap(readiness_status, percentage)
    summary = generate_counsellor_style_summary(percentage, readiness_status, career_direction, total_questions, correct_answers)
    
    if readiness_status == "NOT READY":
        strengths = [
            "Willingness to take assessment and explore options",
            "Opportunity to identify growth areas early",
            "Time available for skill development"
        ]
        weaknesses = [
            "Need for foundational skill development",
            "Requires focused preparation in multiple areas",
            "Career awareness needs to be built"
        ]
    elif readiness_status == "PARTIALLY READY":
        strengths = [
            "Solid foundation in certain areas",
            "Good potential for development",
            "Shows interest in career exploration"
        ]
        weaknesses = [
            "Some areas need further strengthening",
            "Requires continued skill building",
            "Career direction needs refinement"
        ]
    else:
        strengths = [
            "Strong performance in assessment",
            "Good readiness for career exploration",
            "Clear areas of strength identified"
        ]
        weaknesses = [
            "Continue building on strengths",
            "Explore advanced opportunities",
            "Refine career direction with guidance"
        ]
    
    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
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


def generate_and_save_interpretation(
    db: Session,
    test_attempt_id: int,
    total_questions: int,
    correct_answers: int,
    percentage: float
) -> Tuple[InterpretedResult, Dict]:
    """Generate interpretation using Gemini (with fallback) and save to DB"""
    
    scores = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
    section_scores = {}
    category_scores = None
    if scores:
        section_scores = {score.dimension: score.score_value for score in scores if score.dimension.startswith("section_")}
        category_scores = {score.dimension: score.score_value for score in scores}
    
    interpretation_data, error = generate_gemini_interpretation(
        total_questions, correct_answers, percentage, category_scores
    )
    
    is_ai_used = interpretation_data is not None and error is None
    
    if not interpretation_data:
        if error:
            print(f"⚠️ Using fallback interpretation: {error}")
        else:
            print("⚠️ Using fallback interpretation (Gemini unavailable)")
        interpretation_data = generate_fallback_interpretation(
            db, test_attempt_id, total_questions, correct_answers, percentage, section_scores
        )
    else:
        readiness_status, readiness_explanation = calculate_readiness_status(percentage)
        risk_level, risk_explanation = calculate_risk_level(readiness_status)
        
        sections = {}
        section_objs = db.query(Section).all()
        for section in section_objs:
            sections[section.order_index] = section.name
        
        career_direction, career_direction_reason = determine_career_direction(section_scores, sections, percentage)
        roadmap = generate_action_roadmap(readiness_status, percentage)
        
        interpretation_data["readiness_explanation"] = readiness_explanation
        interpretation_data["risk_explanation"] = risk_explanation
        interpretation_data["career_direction"] = career_direction
        interpretation_data["career_direction_reason"] = career_direction_reason
        interpretation_data["roadmap"] = roadmap
    
    interpreted_result = db.query(InterpretedResult).filter(
        InterpretedResult.test_attempt_id == test_attempt_id
    ).first()
    
    if not interpreted_result:
        interpreted_result = InterpretedResult(
            test_attempt_id=test_attempt_id,
            interpretation_text=interpretation_data.get("summary", ""),
            strengths=json.dumps(interpretation_data.get("strengths", [])),
            areas_for_improvement=json.dumps(interpretation_data.get("weaknesses", [])),
            is_ai_generated=is_ai_used
        )
        db.add(interpreted_result)
    else:
        interpreted_result.interpretation_text = interpretation_data.get("summary", interpreted_result.interpretation_text)
        interpreted_result.strengths = json.dumps(interpretation_data.get("strengths", []))
        interpreted_result.areas_for_improvement = json.dumps(interpretation_data.get("weaknesses", []))
        interpreted_result.is_ai_generated = is_ai_used
    
    db.commit()
    db.refresh(interpreted_result)
    
    return interpreted_result, interpretation_data
