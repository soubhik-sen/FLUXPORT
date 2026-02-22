from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def _catalog_path() -> Path:
    configured = (settings.MASS_CHANGE_DATASET_CATALOG_PATH or "").strip()
    if not configured:
        configured = "app/core/decision/mass_change_dataset_catalog.default.json"
    path = Path(configured)
    if path.is_absolute():
        return path
    return Path.cwd() / path


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.exists():
        return {"version": 1, "datasets": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"version": 1, "datasets": []}
    datasets = payload.get("datasets")
    if not isinstance(datasets, list):
        payload["datasets"] = []
    return payload


def clear_mass_change_dataset_cache() -> None:
    _load_catalog.cache_clear()


def get_dataset(dataset_key: str) -> dict[str, Any] | None:
    wanted = (dataset_key or "").strip().lower()
    for raw in _load_catalog().get("datasets", []):
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("dataset_key") or "").strip().lower()
        if key == wanted:
            return raw
    return None


def _is_dataset_enabled_by_flag(row: dict[str, Any]) -> bool:
    flag_name = str(row.get("enabled_flag") or "").strip()
    if not flag_name:
        return True
    return bool(getattr(settings, flag_name, False))


def is_phase1_dataset_enabled(row: dict[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return False
    if not bool(row.get("phase1_enabled", False)):
        return False
    return _is_dataset_enabled_by_flag(row)


def is_workbook_dataset(row: dict[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return False
    return str(row.get("mode") or "").strip().lower() == "workbook"


def list_phase1_datasets() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _load_catalog().get("datasets", []):
        if not isinstance(raw, dict):
            continue
        if not is_phase1_dataset_enabled(raw):
            continue
        rows.append(
            {
                "dataset_key": str(raw.get("dataset_key") or "").strip(),
                "table_name": str(raw.get("table_name") or "").strip(),
                "display_name": str(raw.get("display_name") or "").strip(),
                "category": str(raw.get("category") or "").strip() or "other",
                "mode": str(raw.get("mode") or "").strip().lower() or "single_table",
            }
        )
    rows.sort(key=lambda row: (row["category"], row["display_name"], row["dataset_key"]))
    return rows
