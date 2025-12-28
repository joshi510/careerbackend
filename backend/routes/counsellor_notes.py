from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models import User, UserRole, CounsellorNote, TestAttempt
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/counsellor/notes", tags=["counsellor-notes"])

require_counsellor = require_role([UserRole.COUNSELLOR])


class NoteCreate(BaseModel):
    test_attempt_id: int
    notes: str


class NoteResponse(BaseModel):
    id: int
    counsellor_id: int
    counsellor_name: str
    student_id: int
    test_attempt_id: int
    notes: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_counsellor)
):
    """Create or update counsellor notes for a test attempt"""
    # Verify test attempt exists
    test_attempt = db.query(TestAttempt).filter(
        TestAttempt.id == note_data.test_attempt_id
    ).first()

    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )

    student_id = test_attempt.student_id

    # Check if note already exists
    existing_note = db.query(CounsellorNote).filter(
        CounsellorNote.test_attempt_id == note_data.test_attempt_id,
        CounsellorNote.counsellor_id == current_user.id
    ).first()

    if existing_note:
        # Update existing note
        existing_note.notes = note_data.notes
        existing_note.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_note)

        return NoteResponse(
            id=existing_note.id,
            counsellor_id=existing_note.counsellor_id,
            counsellor_name=current_user.full_name,
            student_id=existing_note.student_id,
            test_attempt_id=existing_note.test_attempt_id,
            notes=existing_note.notes,
            created_at=existing_note.created_at,
            updated_at=existing_note.updated_at
        )
    else:
        # Create new note
        new_note = CounsellorNote(
            counsellor_id=current_user.id,
            student_id=student_id,
            test_attempt_id=note_data.test_attempt_id,
            notes=note_data.notes
        )
        db.add(new_note)
        db.commit()
        db.refresh(new_note)

        return NoteResponse(
            id=new_note.id,
            counsellor_id=new_note.counsellor_id,
            counsellor_name=current_user.full_name,
            student_id=new_note.student_id,
            test_attempt_id=new_note.test_attempt_id,
            notes=new_note.notes,
            created_at=new_note.created_at,
            updated_at=new_note.updated_at
        )


@router.get("/{test_attempt_id}", response_model=Optional[NoteResponse])
async def get_note(
    test_attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get counsellor notes for a test attempt (read-only for all authenticated users)"""
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

    # Get note (any counsellor's note for this attempt)
    note = db.query(CounsellorNote).filter(
        CounsellorNote.test_attempt_id == test_attempt_id
    ).first()

    if not note:
        return None

    # Get counsellor name
    counsellor = db.query(User).filter(User.id == note.counsellor_id).first()

    return NoteResponse(
        id=note.id,
        counsellor_id=note.counsellor_id,
        counsellor_name=counsellor.full_name if counsellor else "Unknown",
        student_id=note.student_id,
        test_attempt_id=note.test_attempt_id,
        notes=note.notes,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

