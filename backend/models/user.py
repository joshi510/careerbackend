from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func
import enum
from database import Base


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    COUNSELLOR = "COUNSELLOR"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

