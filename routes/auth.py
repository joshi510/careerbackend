from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext
from models.user import User, UserRole
from models.student import Student
from auth.jwt import create_access_token
from auth.dependencies import get_current_user, require_admin
import hashlib

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash (supports plain text for dev)"""
    # TEMP DEV MODE: Check if password_hash is plain text (not bcrypt format)
    # Bcrypt hashes start with $2b$ or $2a$ and are 60 chars long
    if not hashed_password.startswith("$2") or len(hashed_password) < 60:
        # Plain text comparison for dev mode
        return plain_password == hashed_password
    
    # Normal bcrypt verification for production
    sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    
    return pwd_context.verify(sha256_hash, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(sha256_hash )


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    mobile_number: str
    education: str
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any non-digit characters
        digits_only = ''.join(filter(str.isdigit, v))
        if not (10 <= len(digits_only) <= 15):
            raise ValueError('Mobile number must be between 10 and 15 digits')
        return digits_only


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Student self-registration - ATOMIC: Creates User and Student in single transaction"""
    print(f"\n{'='*50}")
    print(f"🔵 REGISTRATION REQUEST RECEIVED")
    print(f"   Email: {user_data.email}")
    print(f"   Full Name: {user_data.full_name}")
    print(f"   Mobile: {user_data.mobile_number}")
    print(f"   Education: {user_data.education}")
    print(f"{'='*50}\n")
    
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if mobile number already exists (only if not empty)
        if user_data.mobile_number:
            existing_mobile = db.query(Student).filter(Student.mobile_number == user_data.mobile_number).first()
            if existing_mobile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mobile number already registered"
                )
        
        # Create new student user - registration is always for STUDENT role
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            full_name=user_data.full_name,
            role=UserRole.STUDENT
        )
        
        db.add(new_user)
        db.flush()  # Get user.id without committing
        
        print(f"🔵 User created with ID: {new_user.id}, role: {new_user.role.value}")
        
        # Create student profile - ATOMIC with user creation
        student_profile = Student(
            user_id=new_user.id,
            mobile_number=user_data.mobile_number,
            education=user_data.education
        )
        
        db.add(student_profile)
        print(f"✅ Student profile created for user ID: {new_user.id}")
        
        # Commit both user and student together in single atomic transaction
        db.commit()
        print(f"✅ Transaction committed - User ID: {new_user.id}, Student profile ID: {student_profile.id}")
        
        # Refresh to get database-generated values
        db.refresh(new_user)
        db.refresh(student_profile)
        
    except HTTPException:
        # Re-raise HTTP exceptions (already have proper status codes)
        db.rollback()
        raise
    except Exception as e:
        # Rollback entire transaction on ANY exception
        db.rollback()
        print(f"❌ Registration failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(new_user.id), "role": new_user.role.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role
        )
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        print(f"❌ Login failed: User not found for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    password_valid = verify_password(form_data.password, user.password_hash)
    if not password_valid:
        print(f"❌ Login failed: Invalid password for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ Login successful: {user.email} (role: {user.role.value})")
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role
        )
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role
    )


@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """Create Counsellor or Admin user (Admin only)"""
    if user_data.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /register endpoint for student registration"
        )
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role
    )

