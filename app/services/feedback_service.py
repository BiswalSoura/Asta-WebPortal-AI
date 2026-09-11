"""Rating-only feedback; unique message_id implements idempotent first submission."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.database.models.conversation import Feedback, Message
from app.services.knowledge_operations import OperationsError


async def record_feedback(session, *, conversation_id, message_id, is_positive):
    # Lock prevents concurrent deletion while validating and recording the reference.
    message = (await session.execute(select(Message.id).where(
        Message.id == message_id, Message.conversation_id == conversation_id,
        Message.role == 'assistant').with_for_update())).scalar_one_or_none()
    if message is None:
        raise OperationsError('MESSAGE_NOT_FOUND', 404)
    await session.execute(insert(Feedback).values(message_id=message_id,
        is_positive=is_positive, comment=None).on_conflict_do_nothing(index_elements=['message_id']))
    rating = await session.scalar(select(Feedback.is_positive).where(Feedback.message_id == message_id))
    if rating != is_positive:
        raise OperationsError('FEEDBACK_ALREADY_RECORDED', 409)
    return {"status": "recorded"}
