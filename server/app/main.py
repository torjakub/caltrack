from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, foods, health, llm, logs, nutrients, profile, recipes, sync, targets

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
