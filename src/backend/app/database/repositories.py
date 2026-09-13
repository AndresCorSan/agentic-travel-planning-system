"""CRUD helpers for conversations + message log."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, Message


async def ensure_conversation(session: AsyncSession, conversation_id: str, title: str = "New trip") -> Conversation:
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        conv = Conversation(id=conversation_id, title=title)
        session.add(conv)
        await session.flush()
    return conv


async def list_conversations(session: AsyncSession) -> list[Conversation]:
    res = await session.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    return list(res.scalars().all())


async def get_messages(session: AsyncSession, conversation_id: str) -> list[Message]:
    res = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.asc())
    )
    return list(res.scalars().all())


async def add_message(
    session: AsyncSession,
    conversation_id: str,
    role: str,
    kind: str,
    text: str,
    payload: dict | None = None,
) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, kind=kind, text=text or "", payload=payload)
    session.add(msg)
    await session.flush()
    return msg


async def rename_conversation(session: AsyncSession, conversation_id: str, title: str) -> Conversation | None:
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        return None
    conv.title = title
    await session.flush()
    return conv


async def delete_conversation(session: AsyncSession, conversation_id: str) -> bool:
    await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
    res = await session.execute(delete(Conversation).where(Conversation.id == conversation_id))
    return bool(res.rowcount)
