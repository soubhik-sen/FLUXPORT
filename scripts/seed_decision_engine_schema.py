from __future__ import annotations

import argparse
import enum
import os
import uuid
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy import MetaData, Table, create_engine, func, select


TABLE_DECISION_TABLES = "decision_tables"
TABLE_DECISION_RULES = "decision_rules"
TABLE_ATTRIBUTE_REGISTRY = "attribute_registry"
SUPPORTED_TABLES = (
    TABLE_DECISION_TABLES,
    TABLE_DECISION_RULES,
    TABLE_ATTRIBUTE_REGISTRY,
)

HIT_POLICY_VALUES = {"FIRST_HIT", "COLLECT_ALL", "UNIQUE"}
RESOLUTION_STRATEGY_VALUES = {"DIRECT", "ASSOCIATION", "EXTERNAL"}


@dataclass(frozen=True)
class SyncStats:
    source_count: int
    inserted: int
    updated: int
    unchanged: int
    target_count: int


def _normalize_enum(value: Any) -> str:
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _load_table(conn: sa.Connection, table_name: str) -> Table:
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=conn)


def _fetch_rows(conn: sa.Connection, table: Table) -> list[dict[str, Any]]:
    rows = conn.execute(select(table)).mappings().all()
    return [dict(row) for row in rows]


def _count_rows(conn: sa.Connection, table: Table) -> int:
    return int(conn.execute(select(func.count()).select_from(table)).scalar_one())


def _expect_uuid(value: Any, *, label: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except Exception as exc:
        raise ValueError(f"Invalid UUID for {label}: {value}") from exc


def _validate_decision_table_row(row: dict[str, Any]) -> None:
    _expect_uuid(row.get("id"), label="decision_tables.id")
    slug = str(row.get("slug") or "").strip()
    if not slug:
        raise ValueError("decision_tables.slug cannot be empty")
    hit_policy = _normalize_enum(row.get("hit_policy")).strip().upper()
    if hit_policy not in HIT_POLICY_VALUES:
        raise ValueError(f"Unsupported hit_policy '{hit_policy}' for slug={slug}")
    if not isinstance(row.get("input_schema"), dict):
        raise ValueError(f"decision_tables.input_schema must be JSON object for slug={slug}")
    if not isinstance(row.get("output_schema"), dict):
        raise ValueError(f"decision_tables.output_schema must be JSON object for slug={slug}")


def _validate_decision_rule_row(row: dict[str, Any]) -> None:
    _expect_uuid(row.get("id"), label="decision_rules.id")
    _expect_uuid(row.get("table_id"), label="decision_rules.table_id")
    if row.get("priority") is None:
        raise ValueError("decision_rules.priority cannot be null")
    if not isinstance(row.get("logic"), dict):
        raise ValueError("decision_rules.logic must be JSON object")


def _validate_attribute_registry_row(row: dict[str, Any]) -> None:
    _expect_uuid(row.get("id"), label="attribute_registry.id")
    target_object = str(row.get("target_object") or "").strip()
    attribute_name = str(row.get("attribute_name") or "").strip()
    if not target_object:
        raise ValueError("attribute_registry.target_object cannot be empty")
    if not attribute_name:
        raise ValueError("attribute_registry.attribute_name cannot be empty")
    strategy = _normalize_enum(row.get("resolution_strategy")).strip().upper()
    if strategy not in RESOLUTION_STRATEGY_VALUES:
        raise ValueError(
            f"Unsupported resolution_strategy '{strategy}' "
            f"for {target_object}.{attribute_name}"
        )
    if not isinstance(row.get("path_logic"), dict):
        raise ValueError(
            f"attribute_registry.path_logic must be JSON object for {target_object}.{attribute_name}"
        )


def _sync_decision_tables(
    target_conn: sa.Connection,
    target_table: Table,
    source_rows: list[dict[str, Any]],
) -> SyncStats:
    existing_rows = _fetch_rows(target_conn, target_table)
    existing_by_slug = {str(row["slug"]): row for row in existing_rows}
    source_count = len(source_rows)
    inserted = 0
    updated = 0
    unchanged = 0

    for raw in source_rows:
        _validate_decision_table_row(raw)
        row = {
            "id": _expect_uuid(raw["id"], label="decision_tables.id"),
            "slug": str(raw["slug"]).strip(),
            "object_type": str(raw.get("object_type") or "").strip(),
            "description": str(raw.get("description") or ""),
            "hit_policy": _normalize_enum(raw["hit_policy"]).strip().upper(),
            "input_schema": dict(raw["input_schema"]),
            "output_schema": dict(raw["output_schema"]),
        }
        current = existing_by_slug.get(row["slug"])
        if current is None:
            target_conn.execute(sa.insert(target_table).values(**row))
            inserted += 1
            continue

        current_id = _expect_uuid(current["id"], label="target decision_tables.id")
        if current_id != row["id"]:
            raise ValueError(
                "Cannot preserve source UUIDs: existing decision_tables row has same slug "
                f"'{row['slug']}' but different id (target={current_id}, source={row['id']})."
            )

        current_payload = {
            "object_type": str(current.get("object_type") or ""),
            "description": str(current.get("description") or ""),
            "hit_policy": _normalize_enum(current["hit_policy"]).strip().upper(),
            "input_schema": current["input_schema"] if isinstance(current["input_schema"], dict) else {},
            "output_schema": current["output_schema"] if isinstance(current["output_schema"], dict) else {},
        }
        desired_payload = {
            "object_type": row["object_type"],
            "description": row["description"],
            "hit_policy": row["hit_policy"],
            "input_schema": row["input_schema"],
            "output_schema": row["output_schema"],
        }
        if current_payload == desired_payload:
            unchanged += 1
            continue

        target_conn.execute(
            sa.update(target_table)
            .where(target_table.c.id == row["id"])
            .values(**desired_payload)
        )
        updated += 1

    return SyncStats(
        source_count=source_count,
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        target_count=_count_rows(target_conn, target_table),
    )


def _sync_decision_rules(
    target_conn: sa.Connection,
    target_table: Table,
    source_rows: list[dict[str, Any]],
    target_decision_tables: Table,
) -> SyncStats:
    existing_rows = _fetch_rows(target_conn, target_table)
    existing_by_id = {_expect_uuid(row["id"], label="target decision_rules.id"): row for row in existing_rows}
    valid_table_ids = {
        _expect_uuid(row["id"], label="target decision_tables.id")
        for row in _fetch_rows(target_conn, target_decision_tables)
    }

    source_count = len(source_rows)
    inserted = 0
    updated = 0
    unchanged = 0

    for raw in source_rows:
        _validate_decision_rule_row(raw)
        row_id = _expect_uuid(raw["id"], label="decision_rules.id")
        table_id = _expect_uuid(raw["table_id"], label="decision_rules.table_id")
        if table_id not in valid_table_ids:
            raise ValueError(
                f"decision_rules.table_id {table_id} not found in target decision_tables."
            )
        row = {
            "id": row_id,
            "table_id": table_id,
            "priority": int(raw["priority"]),
            "logic": dict(raw["logic"]),
        }
        current = existing_by_id.get(row_id)
        if current is None:
            target_conn.execute(sa.insert(target_table).values(**row))
            inserted += 1
            continue

        current_payload = {
            "table_id": _expect_uuid(current["table_id"], label="target decision_rules.table_id"),
            "priority": int(current["priority"]),
            "logic": current["logic"] if isinstance(current["logic"], dict) else {},
        }
        desired_payload = {
            "table_id": row["table_id"],
            "priority": row["priority"],
            "logic": row["logic"],
        }
        if current_payload == desired_payload:
            unchanged += 1
            continue

        target_conn.execute(
            sa.update(target_table)
            .where(target_table.c.id == row_id)
            .values(**desired_payload)
        )
        updated += 1

    return SyncStats(
        source_count=source_count,
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        target_count=_count_rows(target_conn, target_table),
    )


def _sync_attribute_registry(
    target_conn: sa.Connection,
    target_table: Table,
    source_rows: list[dict[str, Any]],
) -> SyncStats:
    existing_rows = _fetch_rows(target_conn, target_table)
    existing_by_key = {
        (str(row["target_object"]), str(row["attribute_name"])): row
        for row in existing_rows
    }
    source_count = len(source_rows)
    inserted = 0
    updated = 0
    unchanged = 0

    for raw in source_rows:
        _validate_attribute_registry_row(raw)
        row = {
            "id": _expect_uuid(raw["id"], label="attribute_registry.id"),
            "target_object": str(raw["target_object"]).strip(),
            "attribute_name": str(raw["attribute_name"]).strip(),
            "resolution_strategy": _normalize_enum(raw["resolution_strategy"]).strip().upper(),
            "path_logic": dict(raw["path_logic"]),
        }
        key = (row["target_object"], row["attribute_name"])
        current = existing_by_key.get(key)
        if current is None:
            target_conn.execute(sa.insert(target_table).values(**row))
            inserted += 1
            continue

        current_id = _expect_uuid(current["id"], label="target attribute_registry.id")
        if current_id != row["id"]:
            raise ValueError(
                "Cannot preserve source UUIDs: existing attribute_registry row has same key "
                f"{key} but different id (target={current_id}, source={row['id']})."
            )

        current_payload = {
            "resolution_strategy": _normalize_enum(current["resolution_strategy"]).strip().upper(),
            "path_logic": current["path_logic"] if isinstance(current["path_logic"], dict) else {},
        }
        desired_payload = {
            "resolution_strategy": row["resolution_strategy"],
            "path_logic": row["path_logic"],
        }
        if current_payload == desired_payload:
            unchanged += 1
            continue

        target_conn.execute(
            sa.update(target_table)
            .where(target_table.c.id == row["id"])
            .values(**desired_payload)
        )
        updated += 1

    return SyncStats(
        source_count=source_count,
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        target_count=_count_rows(target_conn, target_table),
    )


def _print_stats(table_name: str, stats: SyncStats) -> None:
    print(
        f"{table_name}: source={stats.source_count}, inserted={stats.inserted}, "
        f"updated={stats.updated}, unchanged={stats.unchanged}, target={stats.target_count}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-time, idempotent seed from enterprise decision engine DB to FLUXPORT DB "
            "for decision_tables, decision_rules, and attribute_registry."
        )
    )
    parser.add_argument(
        "--source-db-url",
        default=os.getenv("SOURCE_DATABASE_URL", "").strip(),
        help="Source decision engine database URL (or set SOURCE_DATABASE_URL).",
    )
    parser.add_argument(
        "--target-db-url",
        default=os.getenv("TARGET_DATABASE_URL", "").strip(),
        help="Target FLUXPORT database URL (or set TARGET_DATABASE_URL).",
    )
    args = parser.parse_args()

    source_db_url = args.source_db_url or _require_env("SOURCE_DATABASE_URL")
    target_db_url = args.target_db_url or _require_env("TARGET_DATABASE_URL")

    source_engine = create_engine(source_db_url, pool_pre_ping=True)
    target_engine = create_engine(target_db_url, pool_pre_ping=True)

    try:
        with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
            source_tables = {name: _load_table(source_conn, name) for name in SUPPORTED_TABLES}
            target_tables = {name: _load_table(target_conn, name) for name in SUPPORTED_TABLES}

            source_decision_tables = _fetch_rows(source_conn, source_tables[TABLE_DECISION_TABLES])
            source_decision_rules = _fetch_rows(source_conn, source_tables[TABLE_DECISION_RULES])
            source_attribute_registry = _fetch_rows(source_conn, source_tables[TABLE_ATTRIBUTE_REGISTRY])

            dt_stats = _sync_decision_tables(
                target_conn,
                target_tables[TABLE_DECISION_TABLES],
                source_decision_tables,
            )
            dr_stats = _sync_decision_rules(
                target_conn,
                target_tables[TABLE_DECISION_RULES],
                source_decision_rules,
                target_tables[TABLE_DECISION_TABLES],
            )
            ar_stats = _sync_attribute_registry(
                target_conn,
                target_tables[TABLE_ATTRIBUTE_REGISTRY],
                source_attribute_registry,
            )

            print("Seed summary")
            _print_stats(TABLE_DECISION_TABLES, dt_stats)
            _print_stats(TABLE_DECISION_RULES, dr_stats)
            _print_stats(TABLE_ATTRIBUTE_REGISTRY, ar_stats)

            mismatches = []
            for name, stats in (
                (TABLE_DECISION_TABLES, dt_stats),
                (TABLE_DECISION_RULES, dr_stats),
                (TABLE_ATTRIBUTE_REGISTRY, ar_stats),
            ):
                if stats.source_count != stats.target_count:
                    mismatches.append(name)
            if mismatches:
                raise RuntimeError(
                    "Source/target row-count mismatch after seed for: "
                    + ", ".join(mismatches)
                )
            print("Seed completed successfully with matching source/target counts.")
        return 0
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
