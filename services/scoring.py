from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Dict
from models import Answer, Score, TestAttempt, Question, TestStatus


def calculate_raw_scores(db: Session, test_attempt_id: int) -> List[Dict]:
    """
    Calculate raw scores from answers and store them securely.
    Returns list of score dictionaries for storage.
    """
    test_attempt = db.query(TestAttempt).filter(TestAttempt.id == test_attempt_id).first()
    if not test_attempt:
        raise ValueError("Test attempt not found")
    
    answers = db.query(Answer).filter(Answer.test_attempt_id == test_attempt_id).all()
    
    if not answers:
        return []
    
    # Group answers by category/dimension
    dimension_scores = {}
    
    for answer in answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        if not question:
            continue
        
        if question.section_id:
            from models import Section
            section = db.query(Section).filter(Section.id == question.section_id).first()
            if section:
                dimension = f"section_{section.order_index}"
            else:
                dimension = question.category or f"section_unknown_{question.section_id}"
        else:
            dimension = question.category or "general"
        
        if not dimension.startswith("section_") and question.category:
            dimension = question.category
        
        if dimension not in dimension_scores:
            dimension_scores[dimension] = {
                "total": 0,
                "count": 0,
                "values": []
            }
        
        # Parse answer value based on question type
        # Likert scale mapping: A=1, B=2, C=3, D=4, E=5
        answer_text_upper = answer.answer_text.strip().upper()
        likert_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        
        if question.question_type.value == "LIKERT_SCALE":
            if answer_text_upper in likert_map:
                value = float(likert_map[answer_text_upper])
            else:
                print(f"⚠️ Invalid Likert answer '{answer.answer_text}' for question {question.id}, defaulting to 3 (C)")
                value = 3.0
        elif question.question_type.value == "MULTIPLE_CHOICE":
            if answer_text_upper in likert_map:
                value = float(likert_map[answer_text_upper])
            else:
                try:
                    value = float(answer.answer_text)
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid MCQ answer '{answer.answer_text}' for question {question.id}, defaulting to 0")
                    value = 0.0
        else:
            value = 0.0
        
        dimension_scores[dimension]["total"] += value
        dimension_scores[dimension]["count"] += 1
        dimension_scores[dimension]["values"].append(value)
    
    # Calculate scores for each dimension
    scores_to_store = []
    total_all_scores = 0.0
    total_all_count = 0
    
    for dimension, data in dimension_scores.items():
        if data["count"] > 0:
            raw_score = data["total"] / data["count"]
            
            score = Score(
                test_attempt_id=test_attempt_id,
                dimension=dimension,
                score_value=raw_score,
                percentile=None
            )
            db.add(score)
            scores_to_store.append({
                "dimension": dimension,
                "score_value": raw_score,
                "count": data["count"]
            })
            
            total_all_scores += data["total"]
            total_all_count += data["count"]
    
    # Calculate overall score (convert 1-5 average to 0-100 percentage)
    # IMPORTANT: This is the SINGLE source of truth for overall_percentage calculation
    # All other code must retrieve this value from scores table, never recalculate
    if total_all_count > 0:
        average_score = total_all_scores / total_all_count
        overall_score = ((average_score - 1) / 4) * 100.0  # Convert 1-5 scale to 0-100%
        overall_score = min(100.0, max(0.0, overall_score))  # Clamp to valid range
        
        existing_overall = db.query(Score).filter(
            Score.test_attempt_id == test_attempt_id,
            Score.dimension == "overall"
        ).first()
        
        if existing_overall:
            existing_overall.score_value = overall_score
        else:
            overall_score_record = Score(
                test_attempt_id=test_attempt_id,
                dimension="overall",
                score_value=overall_score,
                percentile=None
            )
            db.add(overall_score_record)
        
        scores_to_store.append({
            "dimension": "overall",
            "score_value": overall_score,
            "count": total_all_count
        })
    
    db.commit()
    
    return scores_to_store


def store_scores(db: Session, test_attempt_id: int) -> bool:
    """
    Calculate and store raw scores for a test attempt.
    Returns True if successful.
    """
    try:
        existing_scores = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
        if existing_scores:
            for score in existing_scores:
                db.delete(score)
            db.commit()
        
        calculate_raw_scores(db, test_attempt_id)
        
        return True
    except Exception as e:
        db.rollback()
        raise e

