from dataclasses import dataclass
from uuid import UUID

from app.rag import RAGAnswer


@dataclass(frozen=True)
class ConversationHistoryMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ConversationReply:
    conversation_id: UUID
    answer: RAGAnswer
    contextualized: bool