from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.llm import service
from app.llm.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user=Depends(get_current_user)):
    return ChatResponse(reply=service.chat(body.prompt))
