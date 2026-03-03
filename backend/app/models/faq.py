"""
FAQ model for frequently asked questions.
"""
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class FAQ(Base):
    """FAQ model for storing frequently asked questions."""
    
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False, index=True)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self):
        return f"<FAQ(id={self.id}, question={self.question[:50]}...)>"

