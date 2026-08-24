from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, foods, health, llm, logs, nutrients, profile, recipes, sync, targets

# Fail fast rather than silently serving with forgeable tokens: the default
# secret is public knowledge (it ships in this repo), so anyone could mint
# valid JWTs for any user. Local/dev use is unaffected; set JWT_SECRET in
# production (docs/self-hosting.md).
if settings.environment == "production" and settings.jwt_secret == "dev-secret-change-me":
    raise RuntimeError(
        "JWT_SECRET is not set (or is still the insecure default). "
        "Refusing to start in production — set JWT_SECRET to a long random string."
    )

app = FastAPI(title="calTrack API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(targets.router)
app.include_router(foods.router)
app.include_router(logs.router)
app.include_router(recipes.router)
app.include_router(nutrients.router)
app.include_router(sync.router)
app.include_router(llm.router)
