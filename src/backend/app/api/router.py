from fastapi import APIRouter

from app.api.v1.conversations import router as conversations_router
from app.api.v1.plans import router as plans_router

router = APIRouter(prefix="/api/v1")
router.include_router(conversations_router, tags=["conversations"])
router.include_router(plans_router, tags=["plans"])
