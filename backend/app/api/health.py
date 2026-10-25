from fastapi import APIRouter

from app.config import get_settings
from app.schemas import Health
from app.services import alphavantage

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=Health)
async def get_health() -> Health:
    return Health(
        status="ok",
        llm_model=get_settings().llm_model,
        alphavantage_calls_left=await alphavantage.calls_left_today(),
    )
