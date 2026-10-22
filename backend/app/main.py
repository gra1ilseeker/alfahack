from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, profile, metrics, dashboard, products, ranking, events
from app.core.database import engine, Base
from app.models import user as user_model
from app.models import profile as profile_model
from app.models import product as product_model
from app.models import metric as metric_model
from app.models import ranking as ranking_model
from app.models import event as event_model

app = FastAPI(title="AlfaHack Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(ranking.router, prefix="/rank", tags=["ranking"])
app.include_router(events.router, prefix="/events", tags=["events"])


@app.get("/health")
def health():
    return {"status": "ok"}
