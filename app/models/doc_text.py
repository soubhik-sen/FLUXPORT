from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    func,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocText(Base):
    """
    Scope mapping for text usage.
    Exactly one scope target must be set, aligned to scope_kind.
    """

    __tablename__ = "doc_text"
    __table_args__ = (
        CheckConstraint(
            """
            (
                scope_kind = 'PO'
                AND po_type_id IS NOT NULL
                AND ship_type_id IS NULL
                AND document_type_id IS NULL
            )
            OR
            (
                scope_kind = 'SHIPMENT'
                AND po_type_id IS NULL
                AND ship_type_id IS NOT NULL
                AND document_type_id IS NULL
            )
            OR
            (
                scope_kind = 'DOCUMENT'
                AND po_type_id IS NULL
                AND ship_type_id IS NULL
                AND document_type_id IS NOT NULL
            )
            """,
            name="ck_doc_text_scope_target_match",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text_type_id: Mapped[int] = mapped_column(
        ForeignKey("text_type_lookup.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scope_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    po_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("po_type_lookup.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ship_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("ship_type_lookup.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    document_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_type_lookup.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_master.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    partner_id: Mapped[int | None] = mapped_column(
        ForeignKey("partner_master.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    text_values: Mapped[list["TextVal"]] = relationship(
        "TextVal", back_populates="doc_text", cascade="all, delete-orphan"
    )


class TextVal(Base):
    """
    Localized text payloads for a given doc_text mapping.
    """

    __tablename__ = "text_val"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_text_val_valid_range",
        ),
        Index("ix_text_val_doc_text_language", "doc_text_id", "language"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_text_id: Mapped[int] = mapped_column(
        ForeignKey("doc_text.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[object | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[object | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    doc_text: Mapped["DocText"] = relationship("DocText", back_populates="text_values")
