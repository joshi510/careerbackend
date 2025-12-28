from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Dict
import json
from database import get_db
from models import User, UserRole, TestAttempt, TestStatus, Score, InterpretedResult, Career
from auth.dependencies import require_admin

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


class AnalyticsResponse(BaseModel):
    total_students: int
    total_counsellors: int
    total_attempts: int
    completed_attempts: int
    average_score: float
    readiness_distribution: Dict[str, int]
    career_cluster_distribution: Dict[str, int]


def calculate_readiness_status(percentage: float) -> str:
    """Calculate readiness status from percentage"""
    if percentage >= 80:
        return "READY"
    elif percentage >= 60:
        return "PARTIALLY READY"
    else:
        return "NOT READY"


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get admin analytics (Admin only)"""
    
    # Count users by role
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
    total_counsellors = db.query(User).filter(User.role == UserRole.COUNSELLOR).count()
    
    # Count test attempts
    total_attempts = db.query(TestAttempt).count()
    completed_attempts = db.query(TestAttempt).filter(
        TestAttempt.status == TestStatus.COMPLETED
    ).count()
    
    # Calculate average score
    avg_score_result = db.query(func.avg(Score.score_value)).filter(
        Score.dimension == "overall"
    ).scalar()
    average_score = float(avg_score_result) if avg_score_result else 0.0
    
    # Calculate readiness distribution from scores
    readiness_distribution = {
        'READY': 0,
        'PARTIALLY READY': 0,
        'NOT READY': 0
    }
    
    # Get all completed test attempts with scores
    completed_attempts_query = db.query(TestAttempt).filter(
        TestAttempt.status == TestStatus.COMPLETED
    ).all()
    
    for attempt in completed_attempts_query:
        score = db.query(Score).filter(
            Score.test_attempt_id == attempt.id,
            Score.dimension == "overall"
        ).first()
        
        if score:
            readiness_status = calculate_readiness_status(score.score_value)
            readiness_distribution[readiness_status] = readiness_distribution.get(readiness_status, 0) + 1
    
    # Get career cluster distribution from Career model
    career_cluster_distribution = {}
    careers = db.query(Career).all()
    
    for career in careers:
        # Use category if available, otherwise use career_name
        cluster_name = career.category if career.category else (career.career_name if career.career_name else "Other")
        career_cluster_distribution[cluster_name] = career_cluster_distribution.get(cluster_name, 0) + 1
    
    return AnalyticsResponse(
        total_students=total_students,
        total_counsellors=total_counsellors,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        average_score=round(average_score, 2),
        readiness_distribution=readiness_distribution,
        career_cluster_distribution=career_cluster_distribution
    )

