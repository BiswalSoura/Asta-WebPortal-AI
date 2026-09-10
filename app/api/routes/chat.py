from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_conversation_service,
    get_database_session,
)
from app.conversation import (
    ConversationNotFoundError,
)
from app.schemas.chat import (
    ChatMessageRequest,
    ConversationCreateRequest,
    ChatMessageResponse,
    ChatSourceResponse,
    ConversationCreatedResponse,
)
from app.services import (
    ConversationService,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "/conversations",
    response_model=(
        ConversationCreatedResponse
    ),
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: ConversationCreateRequest | None = None,
    session: AsyncSession = Depends(
        get_database_session
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
) -> ConversationCreatedResponse:
    conversation_id = (
        await service.start_conversation(**(
            {"page_context": {"host_page_context": request.page_context}}
            if request is not None and request.page_context is not None else {}
        ))
    )

    await session.commit()

    return ConversationCreatedResponse(
        conversation_id=conversation_id,
        status="active",
    )


@router.post(
    "/conversations/"
    "{conversation_id}/messages",
    response_model=ChatMessageResponse,
)
async def send_message(
    conversation_id: UUID,
    request: ChatMessageRequest,
    http_request: Request,
    session: AsyncSession = Depends(
        get_database_session
    ),
    service: ConversationService = Depends(
        get_conversation_service
    ),
) -> ChatMessageResponse:
    try:
        result = await service.send_message(
            conversation_id=(
                conversation_id
            ),
            message=request.message,
            request_id=http_request.state.request_id,
        )

        await session.commit()

    except ConversationNotFoundError:
        http_request.state.operational_error_code = "conversation_not_found"
        await session.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Conversation was not found."
            ),
        ) from None

    sources = [
        ChatSourceResponse(
            section_title=(
                source.section_title
            ),
            page_number=(
                source.page_number
            ),
        )
        for source
        in result.answer.sources
    ]

    return ChatMessageResponse(
        conversation_id=(
            result.conversation_id
        ),
        answer=result.answer.answer,
        sources=sources,
    )