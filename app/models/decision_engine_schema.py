from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HitPolicy(str, enum.Enum):
    FIRST_HIT = "FIRST_HIT"
    COLLECT_ALL = "COLLECT_ALL"
    UNIQUE = "UNIQUE"


class ResolutionStrategy(str, enum.Enum):
    DIRECT = "DIRECT"
    ASSOCIATION = "ASSOCIATION"
    EXTERNAL = "EXTERNAL"


class DecisionTable(Base):
    __tablename__ = "decision_tables"
    __table_args__ = (
        Index("ix_decision_tables_slug", "slug", unique=True),
        Index("ix_decision_tables_object_type", "object_type", unique=False),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    slug: Mapped[str] = mapped_column(String, nullable=False)
    object_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("''"),
    )
    description: Mapped[str] = mapped_column(
        String,
        nullable=False,
        server_default=text("''"),
    )
    hit_policy: Mapped[HitPolicy] = mapped_column(
        SAEnum(HitPolicy, name="hit_policy_enum"),
        nullable=False,
        server_default=text("'FIRST_HIT'"),
    )
    input_schema: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    output_schema: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    rules: Mapped[list["DecisionRule"]] = relationship(
        "DecisionRule",
        back_populates="table",
        order_by="DecisionRule.priority",
        cascade="all, delete-orphan",
    )


class DecisionRule(Base):
    __tablename__ = "decision_rules"
    __table_args__ = (
        Index(
            "ix_decision_rules_logic",
            "logic",
            postgresql_using="gin",
            postgresql_ops={"logic": "jsonb_path_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decision_tables.id", ondelete="CASCADE"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    logic: Mapped[dict] = mapped_column(JSONB, nullable=False)

    table: Mapped["DecisionTable"] = relationship(
        "DecisionTable",
        back_populates="rules",
    )


class AttributeRegistry(Base):
    __tablename__ = "attribute_registry"
    __table_args__ = (
        UniqueConstraint(
            "target_object",
            "attribute_name",
            name="uq_attribute_registry_target_attr",
        ),
        Index("ix_attribute_registry_target_object", "target_object"),
        Index("ix_attribute_registry_target_attr", "target_object", "attribute_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    target_object: Mapped[str] = mapped_column(String, nullable=False)
    attribute_name: Mapped[str] = mapped_column(String, nullable=False)
    resolution_strategy: Mapped[ResolutionStrategy] = mapped_column(
        SAEnum(ResolutionStrategy, name="resolution_strategy_enum"),
        nullable=False,
        server_default=text("'DIRECT'"),
    )
    path_logic: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
