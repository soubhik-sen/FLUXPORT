from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin


class EventProfile(AuditMixin, Base):
    __tablename__ = "event_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    effective_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __mapper_args__ = {"version_id_col": version_id}

    events: Mapped[list["ProfileEventMap"]] = relationship(
        "ProfileEventMap",
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class ProfileEventMap(AuditMixin, Base):
    __tablename__ = "profile_event_map"
    __table_args__ = (
        UniqueConstraint("profile_id", "event_code", name="uq_profile_event_map_profile_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("event_profile.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_code: Mapped[str] = mapped_column(
        ForeignKey("event_lookup.event_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    inclusion_rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    anchor_event_code: Mapped[str | None] = mapped_column(
        ForeignKey("event_lookup.event_code", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __mapper_args__ = {"version_id_col": version_id}

    profile: Mapped["EventProfile"] = relationship("EventProfile", back_populates="events")
    event: Mapped["EventLookup"] = relationship(
        "EventLookup",
        foreign_keys=[event_code],
        back_populates="profile_mappings",
    )
    anchor_event: Mapped["EventLookup | None"] = relationship(
        "EventLookup",
        foreign_keys=[anchor_event_code],
        back_populates="anchor_mappings",
    )


class EventInstance(AuditMixin, Base):
    __tablename__ = "event_instance"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED', 'COMPLETED', 'DELAYED')",
            name="ck_event_instance_status",
        ),
        UniqueConstraint("parent_id", "event_code", name="uq_event_instance_parent_event"),
        CheckConstraint(
            "("
            "po_header_id IS NOT NULL AND shipment_header_id IS NULL AND parent_id = po_header_id"
            ") OR ("
            "po_header_id IS NULL AND shipment_header_id IS NOT NULL AND parent_id = shipment_header_id"
            ")",
            name="ck_event_instance_single_parent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    # Logical parent reference required by the business model.
    parent_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Physical FKs to support PO/Shipment polymorphic parent while keeping RESTRICT integrity.
    po_header_id: Mapped[int | None] = mapped_column(
        ForeignKey("po_header.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    shipment_header_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipment_header.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("event_profile.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    shipment_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    event_code: Mapped[str] = mapped_column(
        ForeignKey("event_lookup.event_code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    baseline_date: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    planned_date: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    planned_date_manual_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="UTC",
        server_default=text("'UTC'"),
    )
    actual_date: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")

    __mapper_args__ = {"version_id_col": version_id}

    event: Mapped["EventLookup"] = relationship("EventLookup", back_populates="instances")
    profile: Mapped["EventProfile | None"] = relationship("EventProfile")
    po_header: Mapped["PurchaseOrderHeader | None"] = relationship(
        "PurchaseOrderHeader",
        foreign_keys=[po_header_id],
    )
    shipment_header: Mapped["ShipmentHeader | None"] = relationship(
        "ShipmentHeader",
        foreign_keys=[shipment_header_id],
    )
