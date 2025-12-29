from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # e.g., "Section 1: Logical Reasoning"
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)  # Order of sections (1, 2, 3...)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    questions = relationship("Question", back_populates="section", cascade="all, delete-orphan")
    section_progresses = relationship("SectionProgress", back_populates="section", cascade="all, delete-orphan")

