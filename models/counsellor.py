from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Counsellor(Base):
    __tablename__ = "counsellors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    specialization = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    license_number = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="counsellor_profile")

