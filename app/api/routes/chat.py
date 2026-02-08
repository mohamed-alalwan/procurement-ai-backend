from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List

from app.agents.orchestrator import runProcurementAssistant
from app.core.config import settings


router = APIRouter()


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")

    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

    history: List[HistoryMessage] = Field(default_factory=list)


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.post("/chat")
def chat(body: ChatRequest) -> Dict[str, Any]:
    # Important: keep history trimmed to avoid huge prompts.
    
    history = [h.model_dump() for h in body.history[-5:]]

    result = runProcurementAssistant(
        message=body.message,
        history=history,
        collectionName=settings.mongodbCollection,
    )

    # Normalize response: set answer = clarifyingQuestion if present
    if "clarifyingQuestion" in result and "answer" not in result:
        result["answer"] = result["clarifyingQuestion"]

    return result
