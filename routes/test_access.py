from fastapi import APIRouter, Depends
from models.user import User, UserRole
from auth.dependencies import require_role

router = APIRouter(prefix="/test", tags=["test"])

# Create role-specific dependencies
require_student = require_role([UserRole.STUDENT])
require_counsellor = require_role([UserRole.COUNSELLOR])
require_admin = require_role([UserRole.ADMIN])


@router.get("/student")
async def student_test(current_user: User = Depends(require_student)):
    """Test route - Student access only"""
    return {
        "message": "Student access granted",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_role": current_user.role.value
    }


@router.get("/counsellor")
async def counsellor_test(current_user: User = Depends(require_counsellor)):
    """Test route - Counsellor access only"""
    return {
        "message": "Counsellor access granted",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_role": current_user.role.value
    }


@router.get("/admin")
async def admin_test(current_user: User = Depends(require_admin)):
    """Test route - Admin access only"""
    return {
        "message": "Admin access granted",
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_role": current_user.role.value
    }

