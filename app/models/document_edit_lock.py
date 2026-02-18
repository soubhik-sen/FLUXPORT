from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DocumentEditLock(Base):
    __tablename__ = "document_edit_lock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_session_id: Mapped[str] = mapped_column(String(120), nullable=False)
    lock_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    acquired_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    heartbeat_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    expires_at: Mapped[object] = mapped_column(DateTime, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    released_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
