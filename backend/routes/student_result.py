from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import User, UserRole, InterpretedResult, Career, TestAttempt, TestStatus
from auth.dependencies import require_role

router = APIRouter(prefix="/student/result", tags=["student-result"])

require_student = require_role([UserRole.STUDENT])


DISCLAIMER_TEXT = """This assessment is designed to provide general career guidance and insights. Results are based on your responses and are intended for informational purposes only. They should not be considered as definitive career decisions or professional diagnoses. We recommend consulting with a qualified career counsellor to discuss your results in detail and explore your options further. Individual results may vary, and career success depends on many factors beyond assessment scores."""


class CareerResponse(BaseModel):
    career_name: str
    description: Optional[str]
    category: Optional[str]

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    test_attempt_id: int
    interpretation_text: str
    strengths: Optional[str]
    areas_for_improvement: Optional[str]
    careers: List[CareerResponse]
    created_at: datetime
    disclaimer: str

    class Config:
        from_attributes = True


@router.get("/{test_attempt_id}", response_model=ResultResponse)
async def get_result(
    test_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get student's test result (interpreted data only, no raw scores)"""
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
    
    # Get interpreted result
    interpreted_result = db.query(InterpretedResult).filter(
        InterpretedResult.test_attempt_id == test_attempt_id
    ).first()
    
    if not interpreted_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results are not yet available. Please check back later."
        )
    
    # Get career recommendations (without match scores)
    careers_query = db.query(Career).filter(
        Career.interpreted_result_id == interpreted_result.id
    ).order_by(Career.order_index).all()
    
    # Convert to response format (excluding match_score)
    careers_response = [
        CareerResponse(
            career_name=career.career_name,
            description=career.description,
            category=career.category
        )
        for career in careers_query
    ]
    
    return ResultResponse(
        test_attempt_id=test_attempt_id,
        interpretation_text=interpreted_result.interpretation_text,
        strengths=interpreted_result.strengths,
        areas_for_improvement=interpreted_result.areas_for_improvement,
        careers=careers_response,
        created_at=interpreted_result.created_at,
        disclaimer=DISCLAIMER_TEXT
    )


@router.get("/", response_model=List[ResultResponse])
async def get_all_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Get all test results for the current student"""
    # Get all test attempts for current user
    test_attempts = db.query(TestAttempt).filter(
        TestAttempt.student_id == current_user.id,
        TestAttempt.status == TestStatus.COMPLETED
    ).all()
    
    if not test_attempts:
        return []
    
    results = []
    
    for test_attempt in test_attempts:
        interpreted_result = db.query(InterpretedResult).filter(
            InterpretedResult.test_attempt_id == test_attempt.id
        ).first()
        
        if not interpreted_result:
            continue
        
        # Get career recommendations
        careers_query = db.query(Career).filter(
            Career.interpreted_result_id == interpreted_result.id
        ).order_by(Career.order_index).all()
        
        careers_response = [
            CareerResponse(
                career_name=career.career_name,
                description=career.description,
                category=career.category
            )
            for career in careers_query
        ]
        
        results.append(ResultResponse(
            test_attempt_id=test_attempt.id,
            interpretation_text=interpreted_result.interpretation_text,
            strengths=interpreted_result.strengths,
            areas_for_improvement=interpreted_result.areas_for_improvement,
            careers=careers_response,
            created_at=interpreted_result.created_at,
            disclaimer=DISCLAIMER_TEXT
        ))
    
    return results

