from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserDepartment(Base):
    __tablename__ = "user_departments"

    __table_args__ = (
        UniqueConstraint("user_id", "department", name="uq_user_departments_user_dept"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    department: Mapped[str] = mapped_column(String(80), nullable=False)
