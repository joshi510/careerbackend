from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    date_of_birth = Column(DateTime, nullable=True)
    bio = Column(Text, nullable=True)
    mobile_number = Column(String(15), nullable=True, unique=True, index=True)  # 10-15 digits, nullable for backward compatibility
    education = Column(String(100), nullable=True)  # e.g., "12 Science", "Graduate", nullable for backward compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="student_profile")

