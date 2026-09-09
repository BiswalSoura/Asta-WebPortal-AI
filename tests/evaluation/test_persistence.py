"""Existing local test DB only; no Groq, model inference or internet."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.database.models import Conversation, Message
from app.database.session import create_database_engine
from app.evaluation.live import isolated_conversation
from app.rag.models import RAGAnswer


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_real_repository_evaluation_scope_rolls_back_success_and_failure(fail):
    seen = []

    class Responder:
        async def ask(self, query):
            seen.append(query)
            return RAGAnswer("APN / Parcel Number is a project location method.", (),
                             None, None, None, None, False)

    engine = create_database_engine(get_settings().test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            conversation_id = None
            try:
                async with isolated_conversation(session, Responder()) as (service, conversation_id):
                    await service.send_message(conversation_id=conversation_id,
                                               message="Where can I enter parcel information for the project location?")
                    reply = await service.send_message(conversation_id=conversation_id,
                                                       message="Can you explain that option?")
                    assert reply.contextualized
                    assert "APN" in seen[-1]
                    assert await session.scalar(select(func.count()).select_from(Message).where(
                        Message.conversation_id == conversation_id)) == 4
                    if fail:
                        raise RuntimeError("controlled evaluation failure")
            except RuntimeError:
                assert fail
            assert conversation_id is not None
            assert await session.get(Conversation, conversation_id) is None
            assert await session.scalar(select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation_id)) == 0
            await session.rollback()
    finally:
        await engine.dispose()
