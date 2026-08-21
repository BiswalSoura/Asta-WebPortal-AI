from __future__ import annotations

from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Conversation(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "conversations"

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        index=True,
    )

    user_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    page_context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    permission_context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    message_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages",
    )

    feedback: Mapped[Feedback | None] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Feedback(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "feedback"

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "messages.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    is_positive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message: Mapped[Message] = relationship(
        back_populates="feedback",
    )