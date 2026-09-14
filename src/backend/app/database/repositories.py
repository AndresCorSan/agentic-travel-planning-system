"""CRUD helpers for conversations + message log."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Conversation, Message, SavedPlan


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


async def create_saved_plan(
    session: AsyncSession,
    conversation_id: str,
    title: str,
    description: str,
    requirements: list | None,
    plan: dict | None,
) -> SavedPlan:
    row = SavedPlan(
        conversation_id=conversation_id,
        title=title,
        description=description,
        requirements=requirements,
        plan=plan,
    )
    session.add(row)
    await session.flush()
    return row


async def list_saved_plans(session: AsyncSession) -> list[SavedPlan]:
    res = await session.execute(select(SavedPlan).order_by(SavedPlan.created_at.desc()))
    return list(res.scalars().all())


async def get_saved_plan(session: AsyncSession, plan_id: int) -> SavedPlan | None:
    return await session.get(SavedPlan, plan_id)


async def rename_saved_plan(session: AsyncSession, plan_id: int, title: str) -> SavedPlan | None:
    row = await session.get(SavedPlan, plan_id)
    if row is None:
        return None
    row.title = title
    await session.flush()
    return row


async def delete_saved_plan(session: AsyncSession, plan_id: int) -> bool:
    res = await session.execute(delete(SavedPlan).where(SavedPlan.id == plan_id))
    return bool(res.rowcount)
