from fastapi import APIRouter

from . import (
    tournaments,
    athletes,
    # categories,
    # athlete_import,
    # clubs,
    # coaches,
    # kata_groups,
    # kata_draw,
    # kumite_draw,
    # kumite_competition,
    # kata_competition,
)


# ============================================================
# Main API Router
# ============================================================

api_router = APIRouter()

api_router.include_router(tournaments.router)
api_router.include_router(athletes.router)
# api_router.include_router(categories.router)
# api_router.include_router(athlete_import.router)
# api_router.include_router(clubs.router)
# api_router.include_router(coaches.router)
# api_router.include_router(kata_groups.router)
# api_router.include_router(kata_draw.router)
# api_router.include_router(kumite_draw.router)
# api_router.include_router(kumite_competition.router)
# api_router.include_router(kata_competition.router)