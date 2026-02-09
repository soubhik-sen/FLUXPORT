from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="system@local",
        server_default=text("'system@local'"),
    )
    last_changed_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="system@local",
        server_default=text("'system@local'"),
    )
