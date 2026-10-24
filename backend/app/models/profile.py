from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    industry = Column(String, nullable=True)
    revenue_band = Column(String, nullable=True)
    employees = Column(Integer, nullable=True)
    goals = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    metrics = relationship("Metric", back_populates="profile")
    rankings = relationship("Ranking", back_populates="profile")
