from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes import tournaments, athletes, categories, athlete_import, clubs, coaches

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Karate Tournament API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS"
    ],
    allow_headers=[
        "Content-Type",
        "Authorization"
    ],
)

app.include_router(tournaments.router)
app.include_router(athletes.router)
app.include_router(categories.router)
app.include_router(athlete_import.router)
app.include_router(clubs.router)
app.include_router(coaches.router)

@app.get("/")
def root():
    return {"message":"Karate Tournament API is running"}