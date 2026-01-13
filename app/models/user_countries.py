from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class UserCountry(Base):
    __tablename__ = "user_countries"  # clearer than user_regions

    __table_args__ = (
        UniqueConstraint("user_id", "country_code", name="uq_user_countries_user_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    country_code: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO-2 like "UK", "IN"
