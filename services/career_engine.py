from sqlalchemy.orm import Session
from typing import List, Dict, Tuple
from models import Score, Career, InterpretedResult, TestAttempt


# Internal career mapping with dimension weights
CAREER_MAPPING = {
    "Software Engineer": {
        "weights": {
            "analytical": 0.3,
            "logical": 0.25,
            "problem_solving": 0.25,
            "creativity": 0.1,
            "communication": 0.1
        },
        "category": "Technology",
        "description": "Design and develop software solutions, applications, and systems."
    },
    "Data Scientist": {
        "weights": {
            "analytical": 0.35,
            "logical": 0.3,
            "mathematical": 0.25,
            "communication": 0.1
        },
        "category": "Technology",
        "description": "Analyze complex data to extract insights and build predictive models."
    },
    "Marketing Manager": {
        "weights": {
            "communication": 0.3,
            "creativity": 0.25,
            "leadership": 0.2,
            "analytical": 0.15,
            "social": 0.1
        },
        "category": "Business",
        "description": "Develop and execute marketing strategies to promote products and services."
    },
    "Psychologist": {
        "weights": {
            "empathy": 0.3,
            "communication": 0.25,
            "analytical": 0.2,
            "social": 0.15,
            "patience": 0.1
        },
        "category": "Healthcare",
        "description": "Help individuals understand and overcome mental health challenges."
    },
    "Financial Analyst": {
        "weights": {
            "analytical": 0.35,
            "mathematical": 0.3,
            "logical": 0.2,
            "attention_to_detail": 0.15
        },
        "category": "Finance",
        "description": "Analyze financial data to guide investment and business decisions."
    },
    "Graphic Designer": {
        "weights": {
            "creativity": 0.4,
            "artistic": 0.3,
            "communication": 0.2,
            "attention_to_detail": 0.1
        },
        "category": "Creative",
        "description": "Create visual concepts to communicate ideas and messages."
    },
    "Teacher": {
        "weights": {
            "communication": 0.3,
            "patience": 0.25,
            "empathy": 0.2,
            "leadership": 0.15,
            "social": 0.1
        },
        "category": "Education",
        "description": "Educate and inspire students to achieve their learning goals."
    },
    "Project Manager": {
        "weights": {
            "leadership": 0.3,
            "communication": 0.25,
            "organizational": 0.2,
            "problem_solving": 0.15,
            "analytical": 0.1
        },
        "category": "Business",
        "description": "Plan, execute, and oversee projects to ensure successful completion."
    },
    "Research Scientist": {
        "weights": {
            "analytical": 0.35,
            "logical": 0.3,
            "attention_to_detail": 0.2,
            "creativity": 0.15
        },
        "category": "Science",
        "description": "Conduct research to advance knowledge in various scientific fields."
    },
    "Sales Representative": {
        "weights": {
            "communication": 0.35,
            "social": 0.25,
            "persuasion": 0.2,
            "resilience": 0.2
        },
        "category": "Business",
        "description": "Build relationships with clients and drive product sales."
    }
}


def normalize_dimension_name(dimension: str) -> str:
    """Normalize dimension names to match career mapping"""
    dimension_lower = dimension.lower().replace(" ", "_").replace("-", "_")
    
    # Common dimension mappings
    dimension_map = {
        "analytical_thinking": "analytical",
        "logical_reasoning": "logical",
        "problem_solving_skills": "problem_solving",
        "creative_thinking": "creativity",
        "communication_skills": "communication",
        "leadership_skills": "leadership",
        "mathematical_ability": "mathematical",
        "social_skills": "social",
        "emotional_intelligence": "empathy",
        "attention_detail": "attention_to_detail",
        "organizational_skills": "organizational"
    }
    
    return dimension_map.get(dimension_lower, dimension_lower)


def calculate_career_fit(scores: Dict[str, float], career_weights: Dict[str, float]) -> float:
    """
    Calculate career fit score using weighted logic.
    Returns a match score between 0 and 100.
    """
    if not scores or not career_weights:
        return 0.0
    
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for dimension, weight in career_weights.items():
        normalized_dim = normalize_dimension_name(dimension)
        
        # Find matching score dimension
        score_value = None
        for score_dim, score_val in scores.items():
            if normalize_dimension_name(score_dim) == normalized_dim:
                score_value = score_val
                break
        
        if score_value is not None:
            # Normalize score to 0-1 range (assuming scores are 0-5 for Likert)
            normalized_score = min(max(score_value / 5.0, 0.0), 1.0)
            total_weighted_score += normalized_score * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    # Calculate weighted average and convert to 0-100 scale
    weighted_avg = total_weighted_score / total_weight if total_weight > 0 else 0.0
    match_score = weighted_avg * 100.0
    
    return round(match_score, 2)


def get_career_recommendations(scores: Dict[str, float], top_n: int = 5) -> List[Dict]:
    """
    Get career recommendations based on weighted score matching.
    Returns list of careers sorted by match score.
    """
    career_scores = []
    
    for career_name, career_data in CAREER_MAPPING.items():
        match_score = calculate_career_fit(scores, career_data["weights"])
        
        career_scores.append({
            "career_name": career_name,
            "match_score": match_score,
            "category": career_data["category"],
            "description": career_data["description"]
        })
    
    # Sort by match score descending
    career_scores.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Return top N recommendations
    return career_scores[:top_n]


def generate_career_recommendations(db: Session, test_attempt_id: int) -> List[Dict]:
    """
    Generate and store career recommendations for a test attempt.
    Returns list of career recommendations.
    """
    # Get all scores for the test attempt
    scores_query = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
    
    if not scores_query:
        return []
    
    # Convert scores to dictionary
    scores_dict = {score.dimension: score.score_value for score in scores_query}
    
    # Get career recommendations
    recommendations = get_career_recommendations(scores_dict, top_n=5)
    
    # Get or create interpreted result
    test_attempt = db.query(TestAttempt).filter(TestAttempt.id == test_attempt_id).first()
    if not test_attempt:
        raise ValueError("Test attempt not found")
    
    interpreted_result = db.query(InterpretedResult).filter(
        InterpretedResult.test_attempt_id == test_attempt_id
    ).first()
    
    if not interpreted_result:
        # Create interpreted result (will be populated by AI later)
        interpreted_result = InterpretedResult(
            test_attempt_id=test_attempt_id,
            interpretation_text="Career recommendations generated",
            is_ai_generated=False
        )
        db.add(interpreted_result)
        db.flush()
    
    # Delete existing career recommendations
    db.query(Career).filter(Career.interpreted_result_id == interpreted_result.id).delete()
    
    # Store new career recommendations
    for idx, rec in enumerate(recommendations):
        career = Career(
            interpreted_result_id=interpreted_result.id,
            career_name=rec["career_name"],
            description=rec["description"],
            match_score=rec["match_score"],
            category=rec["category"],
            order_index=idx
        )
        db.add(career)
    
    db.commit()
    
    return recommendations


def calculate_weighted_scores(db: Session, test_attempt_id: int) -> Dict[str, float]:
    """
    Calculate weighted scores for all dimensions.
    Returns dictionary of dimension -> weighted score.
    """
    scores_query = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
    
    if not scores_query:
        return {}
    
    # Return scores as dictionary
    return {score.dimension: score.score_value for score in scores_query}

