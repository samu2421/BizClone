"""
Service model for business services.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Service(Base):
    """Service model for storing business services."""
    
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    service_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self):
        return f"<Service(id={self.id}, key={self.service_key}, name={self.name})>"

