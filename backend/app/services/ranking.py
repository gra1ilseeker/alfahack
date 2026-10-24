import httpx
from sqlalchemy.orm import Session
from app.models import Ranking, Profile, Product
from app.core.config import settings


async def call_ml_service(profile: Profile, products: list[Product]) -> dict:
    payload = {
        "profile": {
            "industry": profile.industry,
            "revenue_band": profile.revenue_band,
            "employees": profile.employees,
            "goals": profile.goals,
        },
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "rate": p.rate,
                "min_limit": p.min_limit,
                "max_limit": p.max_limit,
                "requirements": p.requirements_json,
            }
            for p in products
        ],
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(settings.ml_service_url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"result": [{"product_id": p.id, "score": 0.5} for p in products]}


def save_ranking(db: Session, profile_id: int, result_json: dict) -> Ranking:
    ranking = Ranking(profile_id=profile_id, result_json=result_json)
    db.add(ranking)
    db.commit()
    db.refresh(ranking)
    return ranking
