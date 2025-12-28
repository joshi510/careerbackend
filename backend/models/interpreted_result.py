from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class InterpretedResult(Base):
    __tablename__ = "interpreted_results"

    id = Column(Integer, primary_key=True, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    interpretation_text = Column(Text, nullable=False)
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    is_ai_generated = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    test_attempt = relationship("TestAttempt", back_populates="interpreted_result")
    careers = relationship("Career", back_populates="interpreted_result", cascade="all, delete-orphan")

