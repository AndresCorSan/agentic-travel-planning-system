"""Request/response DTOs for the conversations + saved-plans endpoints."""

from pydantic import BaseModel

from app.api.v1.titles import DEFAULT_CONVERSATION_TITLE


class CreateConversationRequest(BaseModel):
    title: str = DEFAULT_CONVERSATION_TITLE
    id: str | None = None


class RenameConversationRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    message: str


class ChoiceItem(BaseModel):
    category: str
    option_id: str


class SaveChoicesRequest(BaseModel):
    choices: list[ChoiceItem]


class SavePlanRequest(BaseModel):
    title: str | None = None


class RenamePlanRequest(BaseModel):
    title: str
