from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.session import SessionLocal
from app.services.metadata_framework_service import MetadataFrameworkService


@dataclass(frozen=True)
class SeedSpec:
    type_key: str
    display_name: str
    description: str
    source_path: Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_flux_root() -> Path:
    return Path.home() / "FLUXDUI" / "flux"


def _build_seed_specs(flux_root: Path) -> list[SeedSpec]:
    repo_root = _repo_root()
    return [
        SeedSpec(
            type_key="endpoint_metadata",
            display_name="Endpoint Metadata",
            description="UI/API endpoint wiring metadata.",
            source_path=flux_root / "assets" / "config" / "screen_endpoint_metadata_seed.json",
        ),
        SeedSpec(
            type_key="create_po_route_metadata",
            display_name="Create PO Route Metadata",
            description="User-email based routing between old/new Create PO pages.",
            source_path=flux_root / "assets" / "config" / "create_po_route_metadata_seed.json",
        ),
        SeedSpec(
            type_key="ui_text_metadata",
            display_name="UI Text Metadata",
            description="Translatable/maintainable UI text metadata.",
            source_path=flux_root / "assets" / "config" / "ui_text_metadata_seed.json",
        ),
        SeedSpec(
            type_key="role_scope_policy",
            display_name="Role Scope Policy Metadata",
            description="Role-scope and policy controls for endpoint access/scoping.",
            source_path=repo_root / "app" / "core" / "decision" / "role_scope_policy.default.json",
        ),
    ]


def _load_payload(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"rows": data}
    raise ValueError(f"Unsupported JSON shape in {path}")


def _seed_one(
    *,
    type_key: str,
    display_name: str,
    description: str,
    payload: dict[str, Any],
    actor_email: str,
    force: bool,
) -> tuple[str, int]:
    with SessionLocal() as db:
        registry = MetadataFrameworkService.get_type(db, type_key)
        if registry is None:
            registry = MetadataFrameworkService.ensure_type(
                db,
                type_key=type_key,
                display_name=display_name,
                description=description,
            )

        published = MetadataFrameworkService.get_published(db, type_key)
        if published is not None and not force:
            return ("skipped", published.version_no)

        draft = MetadataFrameworkService.save_draft(
            db,
            type_key=type_key,
            payload=payload,
            actor_email=actor_email,
            note="Initial metadata framework seed from JSON files.",
        )
        result = MetadataFrameworkService.publish(
            db,
            type_key=type_key,
            actor_email=actor_email,
            version_no=draft.version_no,
            note="Publish seeded metadata version.",
        )
        return ("published", result.version_no)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed metadata framework payloads from existing JSON metadata files "
            "and publish as initial versions."
        )
    )
    parser.add_argument(
        "--flux-root",
        type=Path,
        default=_default_flux_root(),
        help="Path to Flutter repo root containing assets/config JSON files.",
    )
    parser.add_argument(
        "--actor-email",
        default="metadata.seed@system.local",
        help="Actor email written to metadata audit/version records.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create and publish new versions even when a published version already exists.",
    )
    args = parser.parse_args()

    flux_root = args.flux_root.resolve()
    specs = _build_seed_specs(flux_root)

    print(f"Using Flutter repo: {flux_root}")
    print(f"Force reseed: {args.force}")

    for spec in specs:
        if not spec.source_path.exists():
            raise FileNotFoundError(
                f"Metadata seed source not found for {spec.type_key}: {spec.source_path}"
            )

    summary: list[tuple[str, str, int]] = []
    for spec in specs:
        payload = _load_payload(spec.source_path)
        status, version_no = _seed_one(
            type_key=spec.type_key,
            display_name=spec.display_name,
            description=spec.description,
            payload=payload,
            actor_email=args.actor_email,
            force=args.force,
        )
        summary.append((spec.type_key, status, version_no))
        print(f"{spec.type_key}: {status} (version={version_no})")

    print("\nSeed summary")
    for type_key, status, version_no in summary:
        print(f"- {type_key}: {status}, version={version_no}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
