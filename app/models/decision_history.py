from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import AuditMixin


class DecisionHistory(AuditMixin, Base):
    __tablename__ = "decision_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    object_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    table_slug: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    evaluated_at: Mapped[object] = mapped_column(DateTime, server_default=func.now(), nullable=False)
