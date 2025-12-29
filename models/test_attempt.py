from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from database import Base


class TestStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(TestStatus), default=TestStatus.IN_PROGRESS, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("User", backref="test_attempts")
    answers = relationship("Answer", back_populates="test_attempt", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="test_attempt", cascade="all, delete-orphan")
    interpreted_result = relationship("InterpretedResult", back_populates="test_attempt", uselist=False, cascade="all, delete-orphan")
    section_progresses = relationship("SectionProgress", back_populates="test_attempt", cascade="all, delete-orphan")

