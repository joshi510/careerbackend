from sqlalchemy import Column, Integer, ForeignKey, String, Text, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Career(Base):
    __tablename__ = "careers"

    id = Column(Integer, primary_key=True, index=True)
    interpreted_result_id = Column(Integer, ForeignKey("interpreted_results.id", ondelete="CASCADE"), nullable=False, index=True)
    career_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)
    category = Column(String(100), nullable=True)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interpreted_result = relationship("InterpretedResult", back_populates="careers")

