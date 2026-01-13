from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    __table_args__ = (
        UniqueConstraint("action_key", "object_type", name="uq_permissions_action_object"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # references domains.technical_key (but cannot enforce domain_name="ACTION" via FK alone)
    action_key: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("domains.technical_key", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    object_type: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("object_types.object_type", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
