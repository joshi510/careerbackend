from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension = Column(String(100), nullable=False)
    score_value = Column(Float, nullable=False)
    percentile = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    test_attempt = relationship("TestAttempt", back_populates="scores")

