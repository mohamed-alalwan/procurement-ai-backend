"""Chat API routes."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/chat")
async def chat():
    """Handle chat requests."""
    pass
