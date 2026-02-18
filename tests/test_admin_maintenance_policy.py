from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.decision.role_scope_metadata import reset_role_scope_metadata_cache
from app.models.roles import Role
from app.models.user_roles import UserRole
from app.models.users import User


def _seed_admin_and_viewer(db_session) -> None:
    db_session.add_all(
        [
            Role(id=1, name="ADMIN_ORG"),
            Role(id=2, name="VIEWER"),
        ]
    )
    db_session.add_all(
        [
            User(
                id=1,
                username="admin",
                email="admin@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=2,
                username="viewer",
                email="viewer@example.com",
                is_active=True,
                clearance=0,
            ),
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            UserRole(user_id=1, role_id=1),
            UserRole(user_id=2, role_id=2),
        ]
    )
    db_session.commit()


@pytest.mark.parametrize(
    "path",
    [
        "/user-partners",
        "/user-customers",
        "/customer-forwarders",
    ],
)
def test_admin_maintenance_routes_enforce_union_metadata_policy(
    client,
    db_session,
    monkeypatch,
    path: str,
):
    _seed_admin_and_viewer(db_session)
    reset_role_scope_metadata_cache()
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_PATH", "")
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", False)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "assets")
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")

    denied = client.get(path, headers={"X-User-Email": "viewer@example.com"})
    assert denied.status_code == 403

    allowed = client.get(path, headers={"X-User-Email": "admin@example.com"})
    assert allowed.status_code == 200
