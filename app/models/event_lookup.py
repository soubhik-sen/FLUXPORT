from sqlalchemy import String, Boolean, DateTime, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class EventLookup(Base):
    """
    Lookup table defining the possible events across the system.
    """

    __tablename__ = "event_lookup"
    __table_args__ = (
        UniqueConstraint("event_code", name="uq_event_lookup_code"),
        CheckConstraint(
            "event_type IN ('EXPECTED', 'UNEXPECTED')",
            name="ck_event_lookup_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="EXPECTED")
    application_object: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

    profile_mappings: Mapped[list["ProfileEventMap"]] = relationship(
        "ProfileEventMap",
        foreign_keys="ProfileEventMap.event_code",
        back_populates="event",
    )
    anchor_mappings: Mapped[list["ProfileEventMap"]] = relationship(
        "ProfileEventMap",
        foreign_keys="ProfileEventMap.anchor_event_code",
        back_populates="anchor_event",
    )
    instances: Mapped[list["EventInstance"]] = relationship(
        "EventInstance",
        back_populates="event",
    )
