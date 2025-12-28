from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class CounsellorNote(Base):
    __tablename__ = "counsellor_notes"

    id = Column(Integer, primary_key=True, index=True)
    counsellor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_attempt_id = Column(Integer, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    counsellor = relationship("User", foreign_keys=[counsellor_id], backref="counsellor_notes")
    student = relationship("User", foreign_keys=[student_id])
    test_attempt = relationship("TestAttempt", backref="counsellor_notes")

