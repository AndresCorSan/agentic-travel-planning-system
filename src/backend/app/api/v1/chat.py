from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from fastapi import APIRouter

from app.agents.ai_models import light_llm

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    response = await light_llm.ainvoke([HumanMessage(content=body.message)])
    content = response.content
    return ChatResponse(reply=content if isinstance(content, str) else str(content))
