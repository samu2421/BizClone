"""
Policy model for business policies.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Policy(Base):
    """Policy model for storing business policies."""
    
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self):
        return f"<Policy(id={self.id}, key={self.policy_key}, name={self.name})>"

