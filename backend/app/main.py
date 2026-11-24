from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.master import Base, master_engine
from app.models import Tournament  # Регистрация модели Master DB
from app.routers import api_router


# ============================================================
# Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    Base.metadata.create_all(bind=master_engine)

    yield

    master_engine.dispose()


# ============================================================
# Application
# ============================================================

app = FastAPI(
    title="Karate Tournament API",
    lifespan=lifespan,
)


# ============================================================
# Middleware
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ============================================================
# API Router
# ============================================================

app.include_router(api_router)


# ============================================================
# Root
# ============================================================

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Karate Tournament API is running"
    }