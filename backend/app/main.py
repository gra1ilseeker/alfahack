from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from app.api.routes import auth, profile, metrics, dashboard, products, ranking, events
from app.core.database import Base, engine

bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="AlfaHack Backend",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

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


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
    )
    components = openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    components["OAuth2Password"] = {
        "type": "oauth2",
        "description": "В Authorize укажите email в поле username и пароль. Запрос пойдёт на /auth/token, токен подставится автоматически.",
        "flows": {
            "password": {
                "tokenUrl": "/auth/token",
                "scopes": {},
            }
        },
    }
    components["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "Token",
        "description": "Если токен уже есть, можно вставить его вручную в формате Bearer <token>",
    }
    openapi_schema["security"] = [{"OAuth2Password": []}, {"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
