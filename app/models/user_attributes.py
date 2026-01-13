from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserAttribute(Base):
    __tablename__ = "user_attributes"

    __table_args__ = (
        # one key per user (prevents duplicates like (user_id=1, key="theme") twice)
        UniqueConstraint("user_id", "key", name="uq_user_attributes_user_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
