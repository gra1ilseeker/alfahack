from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.product import ProductCreate, ProductResponse
from app.services import product as product_service
from app.api.deps import get_db

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return product_service.list_products(db)


@router.post("/", response_model=ProductResponse)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return product_service.create_product(db, **payload.model_dump())
