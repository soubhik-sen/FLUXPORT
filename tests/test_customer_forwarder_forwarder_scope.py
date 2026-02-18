from __future__ import annotations

from app.core.config import settings
from app.core.decision.role_scope_metadata import reset_role_scope_metadata_cache
from app.models.customer_forwarder import CustomerForwarder
from app.models.customer_master import CustomerMaster
from app.models.customer_role import CustomerRole
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.roles import Role
from app.models.user_partner_link import UserPartnerLink
from app.models.user_roles import UserRole
from app.models.users import User


def _seed_scope_data(db_session) -> dict[str, int]:
    db_session.add_all(
        [
            Role(id=1, name="ADMIN_ORG"),
            Role(id=2, name="FORWARDER"),
        ]
    )
    db_session.add_all(
        [
            User(id=1, username="admin", email="admin@example.com", is_active=True, clearance=0),
            User(
                id=2,
                username="forwarder-one-user",
                email="forwarder.one@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=3,
                username="forwarder-two-user",
                email="forwarder.two@example.com",
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
            UserRole(user_id=3, role_id=2),
        ]
    )

    db_session.add(PartnerRole(id=1, role_code="FO", role_name="Forwarder", is_active=True))
    db_session.add_all(
        [
            PartnerMaster(
                id=101,
                partner_identifier="FWD-101",
                role_id=1,
                legal_name="Forwarder One",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            PartnerMaster(
                id=102,
                partner_identifier="FWD-102",
                role_id=1,
                legal_name="Forwarder Two",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
        ]
    )

    db_session.add(CustomerRole(id=1, role_code="B2B", role_name="B2B", is_active=True))
    db_session.add_all(
        [
            CustomerMaster(
                id=201,
                customer_identifier="CUST-201",
                role_id=1,
                legal_name="Customer One",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
            CustomerMaster(
                id=202,
                customer_identifier="CUST-202",
                role_id=1,
                legal_name="Customer Two",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
            CustomerMaster(
                id=203,
                customer_identifier="CUST-203",
                role_id=1,
                legal_name="Customer Three",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
        ]
    )

    db_session.add_all(
        [
            UserPartnerLink(
                user_email="forwarder.one@example.com",
                partner_id=101,
                deletion_indicator=False,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
            UserPartnerLink(
                user_email="forwarder.two@example.com",
                partner_id=102,
                deletion_indicator=False,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
        ]
    )

    db_session.add_all(
        [
            CustomerForwarder(
                id=301,
                customer_id=201,
                forwarder_id=101,
                deletion_indicator=False,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
            CustomerForwarder(
                id=302,
                customer_id=202,
                forwarder_id=102,
                deletion_indicator=False,
                created_by="seed@system.local",
                last_changed_by="seed@system.local",
            ),
        ]
    )
    db_session.commit()
    return {"forwarder_one_id": 101, "forwarder_two_id": 102}


def _enable_union_metadata(monkeypatch) -> None:
    reset_role_scope_metadata_cache()
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_PATH", "")
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", False)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "assets")


def test_forwarder_list_is_scoped_to_own_forwarder(client, db_session, monkeypatch):
    _seed_scope_data(db_session)
    _enable_union_metadata(monkeypatch)

    response = client.get(
        "/customer-forwarders",
        headers={"X-User-Email": "forwarder.one@example.com"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["forwarder_id"] == 101


def test_forwarder_cannot_link_other_forwarder(client, db_session, monkeypatch):
    ids = _seed_scope_data(db_session)
    _enable_union_metadata(monkeypatch)

    forbidden = client.post(
        "/customer-forwarders",
        headers={"X-User-Email": "forwarder.one@example.com"},
        json={"customer_id": 203, "forwarder_id": ids["forwarder_two_id"]},
    )
    assert forbidden.status_code == 403

    allowed = client.post(
        "/customer-forwarders",
        headers={"X-User-Email": "forwarder.one@example.com"},
        json={"customer_id": 203, "forwarder_id": ids["forwarder_one_id"]},
    )
    assert allowed.status_code == 201
    assert allowed.json()["forwarder_id"] == ids["forwarder_one_id"]


def test_admin_org_can_manage_any_forwarder(client, db_session, monkeypatch):
    ids = _seed_scope_data(db_session)
    _enable_union_metadata(monkeypatch)

    response = client.post(
        "/customer-forwarders",
        headers={"X-User-Email": "admin@example.com"},
        json={"customer_id": 203, "forwarder_id": ids["forwarder_two_id"]},
    )
    assert response.status_code == 201
    assert response.json()["forwarder_id"] == ids["forwarder_two_id"]
