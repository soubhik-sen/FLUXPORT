from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SysWorkflowRule(Base):
    __tablename__ = "sys_workflow_rules"

    __table_args__ = (
        UniqueConstraint(
            "doc_category",
            "doc_type_id",
            "state_code",
            "action_key",
            name="uq_workflow_rules_doc_type_state_action",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    doc_category: Mapped[str] = mapped_column(String(20), nullable=False)
    doc_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("document_type_lookup.id", ondelete="RESTRICT"),
        nullable=False,
    )
    state_code: Mapped[str] = mapped_column(String(30), nullable=False)
    action_key: Mapped[str] = mapped_column(String(60), nullable=False)
    required_role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
