from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db.session import SessionLocal
from app.services.metadata_framework_service import MetadataFrameworkService
from app.services.role_scope_policy_validator import (
    REQUIRED_BUSINESS_ENDPOINT_KEYS,
    validate_role_scope_policy_payload,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_policy_path() -> Path:
    return _repo_root() / "app" / "core" / "decision" / "role_scope_policy.default.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _endpoint_keys(payload: dict[str, Any]) -> set[str]:
    rows = payload.get("endpoint_policies") or []
    if not isinstance(rows, list):
        return set()
    keys: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        if raw.get("enabled", True) is False:
            continue
        token = str(raw.get("endpoint") or "").strip().lower()
        if token:
            keys.add(token)
    return keys


def _mapping_fingerprint(payload: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    rows = payload.get("role_scope_mapping") or []
    if not isinstance(rows, list):
        return set()
    values: set[tuple[str, str, str, str]] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        values.add(
            (
                str(raw.get("role") or "").strip().upper(),
                str(raw.get("dimension") or "").strip(),
                " ".join(str(raw.get("source") or "").split()),
                str(raw.get("target_field") or "").strip(),
            )
        )
    return values


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lint role scope policy payload and diff default JSON vs published DB snapshot."
        )
    )
    parser.add_argument(
        "--default-path",
        type=Path,
        default=_default_policy_path(),
        help="Path to default role scope policy JSON file.",
    )
    parser.add_argument(
        "--type-key",
        default="role_scope_policy",
        help="Metadata type key for published payload lookup.",
    )
    args = parser.parse_args()

    default_payload = _load_json(args.default_path.resolve())
    default_issues = validate_role_scope_policy_payload(default_payload)

    with SessionLocal() as db:
        published = MetadataFrameworkService.get_published(db, args.type_key)

    if published is None:
        print(f"No published metadata found for type '{args.type_key}'.")
        published_payload: dict[str, Any] = {}
        published_issues = ["Published payload is missing."]
    else:
        published_payload = published.payload
        published_issues = validate_role_scope_policy_payload(published_payload)

    print(f"Default policy path: {args.default_path.resolve()}")
    if published is not None:
        print(f"Published version: {published.version_no}")
    print("")

    print("Default lint issues:")
    if default_issues:
        for issue in default_issues:
            print(f"- {issue}")
    else:
        print("- none")

    print("\nPublished lint issues:")
    if published_issues:
        for issue in published_issues:
            print(f"- {issue}")
    else:
        print("- none")

    default_keys = _endpoint_keys(default_payload)
    published_keys = _endpoint_keys(published_payload)
    missing_in_published = sorted(default_keys - published_keys)
    extra_in_published = sorted(published_keys - default_keys)
    missing_required = sorted(REQUIRED_BUSINESS_ENDPOINT_KEYS - published_keys)

    print("\nEndpoint drift:")
    print(f"- missing in published vs default: {len(missing_in_published)}")
    for key in missing_in_published:
        print(f"  - {key}")
    print(f"- extra in published vs default: {len(extra_in_published)}")
    for key in extra_in_published:
        print(f"  - {key}")
    print(f"- missing required business keys in published: {len(missing_required)}")
    for key in missing_required:
        print(f"  - {key}")

    default_mappings = _mapping_fingerprint(default_payload)
    published_mappings = _mapping_fingerprint(published_payload)
    missing_mappings = sorted(default_mappings - published_mappings)
    extra_mappings = sorted(published_mappings - default_mappings)
    print("\nRole mapping drift:")
    print(f"- missing mappings in published: {len(missing_mappings)}")
    for role, dimension, source, target in missing_mappings:
        print(f"  - role={role} dimension={dimension} source={source} target={target}")
    print(f"- extra mappings in published: {len(extra_mappings)}")
    for role, dimension, source, target in extra_mappings:
        print(f"  - role={role} dimension={dimension} source={source} target={target}")

    has_errors = bool(
        default_issues
        or published_issues
        or missing_in_published
        or missing_required
        or missing_mappings
    )
    print("\nResult: " + ("FAIL" if has_errors else "PASS"))
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
