from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    period = Column(String, nullable=False)
    revenue = Column(Float, default=0)
    expenses = Column(Float, default=0)
    cash_flow = Column(Float, default=0)
    online_share = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="metrics")
