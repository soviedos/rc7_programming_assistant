from fastapi import APIRouter

from src.api.v1.schemas.chat import ChatRequest, ChatResponse
from src.services.chat.service import build_placeholder_response

router = APIRouter()


@router.post("/generate", response_model=ChatResponse)
async def generate_code(payload: ChatRequest) -> ChatResponse:
    return build_placeholder_response(payload)
