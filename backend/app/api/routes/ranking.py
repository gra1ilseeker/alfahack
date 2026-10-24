from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.ranking import RankRequest, RankResponse
from app.services import ranking as ranking_service
from app.services import profile as profile_service
from app.services import product as product_service
from app.api.deps import get_db

router = APIRouter()


@router.post("/products", response_model=RankResponse)
async def rank_products(payload: RankRequest, db: Session = Depends(get_db)):
    profile = profile_service.get_profile(db, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    products = [p for p in product_service.list_products(db) if p.id in payload.products]
    if not products:
        raise HTTPException(status_code=400, detail="No products found")
    result = await ranking_service.call_ml_service(profile, products)
    ranking = ranking_service.save_ranking(db, profile.id, result)
    return RankResponse(ranking_id=ranking.id, result=result)
