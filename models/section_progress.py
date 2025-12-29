from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from database import Base


class SectionStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class SectionProgress(Base):
    __tablename__ = "section_progresses"

    id = Column(Integer, primary_key=True, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(SectionStatus), default=SectionStatus.NOT_STARTED, nullable=False)
    
    # Timer fields (backend-driven)
    section_start_time = Column(DateTime(timezone=True), nullable=True)  # When section was started
    total_time_spent = Column(Integer, default=0, nullable=False)  # Total seconds spent (accumulated)
    paused_at = Column(DateTime(timezone=True), nullable=True)  # When section was paused (null if running)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_attempt = relationship("TestAttempt", back_populates="section_progresses")
    section = relationship("Section", back_populates="section_progresses")

