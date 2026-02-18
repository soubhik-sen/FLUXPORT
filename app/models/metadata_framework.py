from __future__ import annotations

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MetadataRegistry(Base):
    """
    Registers metadata types managed by the framework.
    Example keys: endpoint_metadata, create_po_route_metadata, role_scope_policy.
    """

    __tablename__ = "metadata_registry"
    __table_args__ = (
        UniqueConstraint("type_key", name="uq_metadata_registry_type_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    json_schema: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    versions: Mapped[list["MetadataVersion"]] = relationship(
        "MetadataVersion",
        back_populates="registry",
        cascade="all, delete-orphan",
    )


class MetadataVersion(Base):
    """
    Stores versioned metadata payloads per type.
    `state` values: DRAFT, PUBLISHED, ARCHIVED.
    """

    __tablename__ = "metadata_version"
    __table_args__ = (
        UniqueConstraint(
            "registry_id",
            "version_no",
            name="uq_metadata_version_registry_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("metadata_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)

    registry: Mapped["MetadataRegistry"] = relationship(
        "MetadataRegistry",
        back_populates="versions",
    )


class MetadataAuditLog(Base):
    """
    Immutable audit trail for metadata lifecycle actions.
    """

    __tablename__ = "metadata_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registry_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("metadata_registry.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
