from fastapi import APIRouter

from app.llm import service
from app.llm.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    return ChatResponse(reply=service.chat(body.prompt))
