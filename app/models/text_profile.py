from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import AuditMixin


class TextProfile(AuditMixin, Base):
    __tablename__ = "text_profile"
    __table_args__ = (
        UniqueConstraint("name", "object_type", name="uq_text_profile_name_object"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    effective_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    text_maps: Mapped[list["ProfileTextMap"]] = relationship(
        "ProfileTextMap",
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class TextProfileRule(AuditMixin, Base):
    __tablename__ = "text_profile_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    object_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, default="*")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("text_profile.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default=text("100"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    effective_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[object | None] = mapped_column(Date, nullable=True)

    profile: Mapped["TextProfile"] = relationship("TextProfile")


class ProfileTextMap(AuditMixin, Base):
    __tablename__ = "profile_text_map"
    __table_args__ = (
        UniqueConstraint("profile_id", "text_type_id", name="uq_profile_text_map_profile_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("text_profile.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text_type_id: Mapped[int] = mapped_column(
        ForeignKey("text_type_lookup.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_editable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    profile: Mapped["TextProfile"] = relationship("TextProfile", back_populates="text_maps")
    text_type: Mapped["TextTypeLookup"] = relationship("TextTypeLookup")
    values: Mapped[list["ProfileTextValue"]] = relationship(
        "ProfileTextValue",
        back_populates="profile_text_map",
        cascade="all, delete-orphan",
    )


class ProfileTextValue(AuditMixin, Base):
    __tablename__ = "profile_text_value"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_text_map_id: Mapped[int] = mapped_column(
        ForeignKey("profile_text_map.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    profile_text_map: Mapped["ProfileTextMap"] = relationship(
        "ProfileTextMap",
        back_populates="values",
    )


class POText(AuditMixin, Base):
    __tablename__ = "po_text"
    __table_args__ = (
        UniqueConstraint("po_header_id", "text_type_id", "language", name="uq_po_text_unique"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_header_id: Mapped[int] = mapped_column(
        ForeignKey("po_header.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("text_profile.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_type_id: Mapped[int] = mapped_column(
        ForeignKey("text_type_lookup.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_user_edited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    text_type: Mapped["TextTypeLookup"] = relationship("TextTypeLookup")
    profile: Mapped["TextProfile | None"] = relationship("TextProfile")


class ShipmentText(AuditMixin, Base):
    __tablename__ = "shipment_text"
    __table_args__ = (
        UniqueConstraint(
            "shipment_header_id",
            "text_type_id",
            "language",
            name="uq_shipment_text_unique",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_header_id: Mapped[int] = mapped_column(
        ForeignKey("shipment_header.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("text_profile.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_type_id: Mapped[int] = mapped_column(
        ForeignKey("text_type_lookup.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_user_edited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    text_type: Mapped["TextTypeLookup"] = relationship("TextTypeLookup")
    profile: Mapped["TextProfile | None"] = relationship("TextProfile")
