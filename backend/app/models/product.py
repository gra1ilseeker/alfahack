from sqlalchemy import Column, Integer, String, Float, JSON

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=True)
    rate = Column(Float, nullable=True)
    min_limit = Column(Float, nullable=True)
    max_limit = Column(Float, nullable=True)
    requirements_json = Column(JSON, nullable=True)
