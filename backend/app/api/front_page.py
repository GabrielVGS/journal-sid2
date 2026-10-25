from fastapi import APIRouter, Request

from app.api.deps import ERROR_RESPONSES, ValidDate
from app.core import limits
from app.domain import front_page
from app.schemas import ApiError, FrontPage

router = APIRouter(prefix="/api", tags=["front page"])


@router.get(
    "/front-page",
    response_model=FrontPage,
    responses={**ERROR_RESPONSES, 429: {"model": ApiError, "description": "Too many new pages."}},
)
async def get_front_page(date: ValidDate, request: Request) -> FrontPage:
    if await front_page.load(date) is None:
        limits.check_new_page(request)
    return await front_page.build_front_page(date)
