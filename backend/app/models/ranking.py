from sqlalchemy import Column, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    result_json = Column(JSON, nullable=False)

    profile = relationship("Profile", back_populates="rankings")
