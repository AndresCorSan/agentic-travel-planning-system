from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router

router = APIRouter(prefix="/api/v1")
router.include_router(chat_router, tags=["chat"])
router.include_router(conversations_router, tags=["conversations"])
