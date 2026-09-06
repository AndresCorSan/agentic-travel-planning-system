from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from app.core.dependencies import get_graph

router = APIRouter()


class SendMessageRequest(BaseModel):
    message: str


class Reply(BaseModel):
    role: str = "assistant"
    kind: str = "text"
    text: str


class SendMessageResponse(BaseModel):
    replies: list[Reply]


def _config(conversation_id: str) -> dict:
    return {"configurable": {"thread_id": conversation_id}}


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(conversation_id: str, body: SendMessageRequest, graph=Depends(get_graph)):
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    config = _config(conversation_id)
    state = await graph.aget_state(config)
    before = len((state.values or {}).get("messages", []) or [])
    if state.interrupts:
        result = await graph.ainvoke(Command(resume=body.message), config=config)
    else:
        result = await graph.ainvoke({"messages": [HumanMessage(content=body.message)]}, config=config)
    new_messages = (result.get("messages", []) or [])[before:]
    replies = [
        Reply(text=m.content)
        for m in new_messages
        if isinstance(m, AIMessage) and isinstance(m.content, str) and m.content and not m.tool_calls
    ]
    state = await graph.aget_state(config)
    for interrupt in state.interrupts:
        if isinstance(interrupt.value, str) and interrupt.value:
            replies.append(Reply(text=interrupt.value))
    return SendMessageResponse(replies=replies)
