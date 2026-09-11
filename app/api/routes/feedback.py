from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, StrictBool
from app.api.dependencies.database import get_database_session
from app.api.routes.operations_common import OperationsRoute, bounded_stream
from app.services.feedback_service import record_feedback


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    conversation_id: UUID
    message_id: UUID
    is_positive: StrictBool


router = APIRouter(prefix='/feedback', tags=['Feedback'], route_class=OperationsRoute)


@router.post('', openapi_extra={"requestBody": {"required": True, "content": {
    "application/json": {"schema": FeedbackRequest.model_json_schema()}}}})
async def submit_feedback(request: Request, session=Depends(get_database_session)):
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise HTTPException(415, detail='JSON_REQUIRED')
    body = b''.join([part async for part in bounded_stream(request, 1024)])
    try:
        payload = FeedbackRequest.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, detail='INVALID_REQUEST') from None
    result = await record_feedback(session, **payload.model_dump())
    await session.commit()
    return result
