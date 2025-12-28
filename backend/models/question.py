from sqlalchemy import Column, Integer, String, Text, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from database import Base


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    LIKERT_SCALE = "LIKERT_SCALE"
    TEXT = "TEXT"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    options = Column(Text, nullable=True)
    correct_answer = Column(String(10), nullable=True)
    category = Column(String(100), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True)  # Link to section, nullable for backward compatibility
    is_active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    section = relationship("Section", back_populates="questions")

