from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserRole
from auth.jwt import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        print(f"❌ No token provided")
        raise credentials_exception

    payload = verify_token(token)
    if payload is None:
        print(f"❌ Token verification failed: payload is None for token: {token[:20]}...")
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        print(f"❌ Token payload missing 'sub'. Payload: {payload}")
        raise credentials_exception
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError) as e:
        print(f"❌ Failed to convert user_id to int: {user_id}, error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        print(f"❌ User not found in database for id: {user_id}")
        raise credentials_exception

    print(f"✅ User authenticated: {user.email} (role: {user.role.value})")
    return user


def require_role(allowed_roles: list[UserRole]):
    def role_checker( request: Request, current_user: User = Depends(get_current_user)) -> User:

        if request.method == "OPTIONS":
            return None
         
        # Compare enum values (current_user.role is UserRole enum, get its string value)
        if current_user.role.value not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    # Compare enum value to ensure consistency
    if current_user.role.value != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
