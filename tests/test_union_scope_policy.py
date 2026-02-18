from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.config import settings
from app.api.v1.endpoints.reports import _resolve_scoped_po_numbers
from app.api.v1.endpoints.shipments import _resolve_grouping_scope
from app.models.company_master import CompanyMaster
from app.models.customer_master import CustomerMaster
from app.models.customer_role import CustomerRole
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.permissions import Permission
from app.models.po_lookups import (
    PurchaseOrderStatusLookup,
    PurchaseOrderTypeLookup,
    PurchaseOrgLookup,
)
from app.models.purchase_order import PurchaseOrderHeader
from app.models.object_types import ObjectType
from app.models.roles import Role
from app.models.role_permissions import RolePermission
from app.models.domains import Domain
from app.models.user_customer_link import UserCustomerLink
from app.models.user_partner_link import UserPartnerLink
from app.models.user_roles import UserRole
from app.models.users import User
from app.services.role_scope_policy import (
    is_scope_denied,
    is_union_scope_enabled_for_endpoint,
    resolve_scope_by_field,
)
from app.services.user_scope_service import resolve_union_scope_ids


@pytest.fixture(autouse=True)
def _default_scope_test_runtime(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "auto")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_ENABLED", False)
    monkeypatch.setattr(settings, "METADATA_FRAMEWORK_READ_MODE", "assets")


def _seed_scope_matrix(db):
    db.add_all(
        [
            Role(id=1, name="FORWARDER"),
            Role(id=2, name="SUPPLIER"),
            Role(id=3, name="USER_PURCH_BUYER"),
            Role(id=4, name="ADMIN_ORG"),
            Role(id=5, name="VIEWER"),
        ]
    )
    db.add_all(
        [
            User(
                id=1,
                username="multi",
                email="multi@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=2,
                username="single",
                email="single@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=3,
                username="nolink",
                email="nolink@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=4,
                username="admin",
                email="admin@example.com",
                is_active=True,
                clearance=0,
            ),
            User(
                id=5,
                username="viewer",
                email="viewer@example.com",
                is_active=True,
                clearance=0,
            ),
        ]
    )
    db.flush()
    db.add_all(
        [
            UserRole(user_id=1, role_id=1),
            UserRole(user_id=1, role_id=2),
            UserRole(user_id=1, role_id=3),
            UserRole(user_id=2, role_id=2),
            UserRole(user_id=3, role_id=2),
            UserRole(user_id=4, role_id=4),
            UserRole(user_id=5, role_id=5),
        ]
    )

    db.add_all(
        [
            PartnerRole(id=1, role_code="FO", role_name="Forwarder", is_active=True),
            PartnerRole(id=2, role_code="SU", role_name="Supplier", is_active=True),
            CustomerRole(id=1, role_code="B2B", role_name="B2B", is_active=True),
        ]
    )
    db.add_all(
        [
            PartnerMaster(
                id=11,
                partner_identifier="FO-0011",
                role_id=1,
                legal_name="Forwarder 11",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            PartnerMaster(
                id=12,
                partner_identifier="FO-0012",
                role_id=1,
                legal_name="Forwarder 12",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            PartnerMaster(
                id=21,
                partner_identifier="SU-0021",
                role_id=2,
                legal_name="Supplier 21",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            PartnerMaster(
                id=22,
                partner_identifier="SU-0022",
                role_id=2,
                legal_name="Supplier 22",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
        ]
    )
    db.add_all(
        [
            CustomerMaster(
                id=31,
                customer_identifier="CUST-0031",
                role_id=1,
                legal_name="Customer 31",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            CustomerMaster(
                id=32,
                customer_identifier="CUST-0032",
                role_id=1,
                legal_name="Customer 32",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
        ]
    )
    db.add_all(
        [
            CompanyMaster(
                id=31,
                company_code="COMP-31",
                branch_code="HQ",
                legal_name="Company 31",
                tax_id="TAX-31",
                default_currency="USD",
                is_active=True,
            ),
            CompanyMaster(
                id=32,
                company_code="COMP-32",
                branch_code="HQ",
                legal_name="Company 32",
                tax_id="TAX-32",
                default_currency="USD",
                is_active=True,
            ),
        ]
    )
    db.add_all(
        [
            UserPartnerLink(
                user_email="multi@example.com",
                partner_id=11,
                deletion_indicator=False,
            ),
            UserPartnerLink(
                user_email="multi@example.com",
                partner_id=21,
                deletion_indicator=False,
            ),
            UserPartnerLink(
                user_email="single@example.com",
                partner_id=21,
                deletion_indicator=False,
            ),
            UserCustomerLink(
                user_email="multi@example.com",
                customer_id=31,
                deletion_indicator=False,
            ),
        ]
    )
    db.add_all(
        [
            PurchaseOrderTypeLookup(id=1, type_code="STD", type_name="Standard", is_active=True),
            PurchaseOrderStatusLookup(id=1, status_code="NEW", status_name="New", is_active=True),
            PurchaseOrgLookup(id=1, org_code="ORG", org_name="Org", is_active=True),
        ]
    )
    db.add_all(
        [
            # Overlapping across supplier+forwarder+customer scopes
            PurchaseOrderHeader(
                id=1,
                po_number="PO-001",
                type_id=1,
                status_id=1,
                purchase_org_id=1,
                company_id=31,
                vendor_id=21,
                forwarder_id=11,
                order_date=date(2025, 1, 1),
                currency="USD",
                total_amount=Decimal("100.00"),
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            # Forwarder-only hit for multi-role scope
            PurchaseOrderHeader(
                id=2,
                po_number="PO-002",
                type_id=1,
                status_id=1,
                purchase_org_id=1,
                company_id=32,
                vendor_id=22,
                forwarder_id=11,
                order_date=date(2025, 1, 1),
                currency="USD",
                total_amount=Decimal("100.00"),
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            # Supplier-only hit for multi-role scope
            PurchaseOrderHeader(
                id=3,
                po_number="PO-003",
                type_id=1,
                status_id=1,
                purchase_org_id=1,
                company_id=32,
                vendor_id=21,
                forwarder_id=12,
                order_date=date(2025, 1, 1),
                currency="USD",
                total_amount=Decimal("100.00"),
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            # Customer-only hit for multi-role scope
            PurchaseOrderHeader(
                id=4,
                po_number="PO-004",
                type_id=1,
                status_id=1,
                purchase_org_id=1,
                company_id=31,
                vendor_id=22,
                forwarder_id=12,
                order_date=date(2025, 1, 1),
                currency="USD",
                total_amount=Decimal("100.00"),
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            # Outside all mapped scopes
            PurchaseOrderHeader(
                id=5,
                po_number="PO-005",
                type_id=1,
                status_id=1,
                purchase_org_id=1,
                company_id=32,
                vendor_id=22,
                forwarder_id=12,
                order_date=date(2025, 1, 1),
                currency="USD",
                total_amount=Decimal("100.00"),
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
        ]
    )
    db.commit()


def _po_numbers(payload: list[dict]) -> set[str]:
    return {row["po_number"] for row in payload}


def _seed_po_create_permission(
    db,
    *,
    permission_id: int = 1,
    action_key: str = "pocreate",
    object_type: str = "PO",
    role_ids: tuple[int, ...] = (3, 1),
):
    db.add(Domain(domain_name="ACTION", technical_key=action_key, display_label="PO Create", is_active=True))
    db.add(ObjectType(object_type=object_type, object_description="Purchase Order"))
    db.flush()
    db.add(Permission(id=permission_id, action_key=action_key, object_type=object_type))
    db.flush()
    db.add_all(
        [
            RolePermission(role_id=role_id, permission_id=permission_id, role_name=f"ROLE-{role_id}")
            for role_id in role_ids
        ]
    )
    db.commit()


def _po_create_payload(
    *,
    company_id: int,
    vendor_id: int,
    forwarder_id: int | None,
) -> dict:
    return {
        "po_number": "PO-NEW-001",
        "type_id": 1,
        "status_id": 1,
        "purchase_org_id": 1,
        "company_id": company_id,
        "vendor_id": vendor_id,
        "forwarder_id": forwarder_id,
        "order_date": "2025-01-02",
        "currency": "USD",
        "total_amount": "0.00",
        "created_by": "seed@local",
        "last_changed_by": "seed@local",
        "items": [],
    }


def test_union_scope_resolver_returns_roles_and_ids(db_session):
    _seed_scope_matrix(db_session)
    scope = resolve_union_scope_ids(db_session, "multi@example.com")

    assert "FORWARDER" in scope.role_names
    assert "SUPPLIER" in scope.role_names
    assert "USER_PURCH_BUYER" in scope.role_names
    assert scope.forwarder_partner_ids == {11}
    assert scope.supplier_partner_ids == {21}
    assert scope.customer_ids == {31}


def test_purchase_orders_union_scope_overlapping_and_disjoint(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)

    response = client.get(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert response.status_code == 200
    assert _po_numbers(response.json()) == {"PO-001", "PO-002", "PO-003", "PO-004"}


def test_po_create_requires_pocreate_permission(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)

    response = client.post(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
        json=_po_create_payload(company_id=31, vendor_id=21, forwarder_id=11),
    )
    assert response.status_code == 403
    assert "Missing permission" in response.json()["detail"]


def test_po_create_enforces_customer_and_forwarder_scope(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    _seed_po_create_permission(db_session)
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "PO_CREATE_PERMISSION_ACTION_KEYS", "pocreate")
    monkeypatch.setattr(settings, "PO_CREATE_PERMISSION_OBJECT_TYPES", "PO")

    bad_company = client.post(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
        json=_po_create_payload(company_id=32, vendor_id=21, forwarder_id=11),
    )
    assert bad_company.status_code == 403
    assert "outside user scope" in bad_company.json()["detail"]

    bad_forwarder = client.post(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
        json=_po_create_payload(company_id=31, vendor_id=21, forwarder_id=12),
    )
    assert bad_forwarder.status_code == 403
    assert "outside user scope" in bad_forwarder.json()["detail"]

    ok = client.post(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
        json=_po_create_payload(company_id=31, vendor_id=21, forwarder_id=11),
    )
    assert ok.status_code == 201
    assert ok.json()["company_id"] == 31
    assert ok.json()["forwarder_id"] == 11


def test_purchase_orders_legacy_scope_precedence(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", False)

    response = client.get(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert response.status_code == 200
    # Legacy precedence: forwarder first, then supplier, then customer.
    assert _po_numbers(response.json()) == {"PO-001", "PO-002"}


def test_purchase_orders_no_scope_user_behavior(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)

    response = client.get(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "nolink@example.com"},
    )
    assert response.status_code == 200
    # Non-scoped user remains unscoped to avoid legacy regressions.
    assert _po_numbers(response.json()) == {"PO-001", "PO-002", "PO-003", "PO-004", "PO-005"}


def test_purchase_orders_single_role_regression(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)

    response = client.get(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "single@example.com"},
    )
    assert response.status_code == 200
    assert _po_numbers(response.json()) == {"PO-001", "PO-003"}


def test_purchase_orders_read_and_workspace_scope(client, db_session, monkeypatch):
    _seed_scope_matrix(db_session)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)

    allowed = client.get(
        "/api/v1/purchase-orders/4",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["po_number"] == "PO-004"

    allowed_workspace = client.get(
        "/api/v1/purchase-orders/workspace/4",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert allowed_workspace.status_code == 200
    assert allowed_workspace.json()["header"]["po_number"] == "PO-004"

    forbidden = client.get(
        "/api/v1/purchase-orders/5",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert forbidden.status_code == 403

    forbidden_workspace = client.get(
        "/api/v1/purchase-orders/workspace/5",
        headers={"X-User-Email": "multi@example.com"},
    )
    assert forbidden_workspace.status_code == 403


def test_reports_and_shipments_scope_follow_feature_flag(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)
    _, union_po_numbers = _resolve_scoped_po_numbers(
        db_session,
        "multi@example.com",
        strict=False,
        forwarder_field="forwarder_id",
    )
    assert set(union_po_numbers) == {"PO-001", "PO-002", "PO-003", "PO-004"}
    union_shipment_scope = _resolve_grouping_scope(db_session, "multi@example.com")
    assert set(union_shipment_scope.keys()) == {"forwarder_id", "vendor_id", "customer_id"}

    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", False)
    _, legacy_po_numbers = _resolve_scoped_po_numbers(
        db_session,
        "multi@example.com",
        strict=False,
        forwarder_field="forwarder_id",
    )
    assert set(legacy_po_numbers) == {"PO-001", "PO-002"}
    legacy_shipment_scope = _resolve_grouping_scope(db_session, "multi@example.com")
    assert set(legacy_shipment_scope.keys()) == {"forwarder_id"}


def test_role_scope_policy_mode_union_overrides_feature_flag(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", False)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert set(scope.keys()) == {"forwarder_id", "vendor_id", "customer_id"}


def test_role_scope_policy_rollout_limits_union_to_targeted_endpoints(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "purchase_orders,reports.*")

    assert is_union_scope_enabled_for_endpoint("purchase_orders")
    assert is_union_scope_enabled_for_endpoint("reports.visibility")
    assert not is_union_scope_enabled_for_endpoint("shipments.from_schedule_lines")

    shipments_scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="shipments.from_schedule_lines",
    )
    assert set(shipments_scope.keys()) == {"forwarder_id"}


def test_role_scope_policy_disabled_preserves_legacy_union_switch(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    # When policy framework is disabled, system should behave exactly like
    # historical UNION_SCOPE_ENABLED-based behavior.
    assert set(scope.keys()) == {"forwarder_id", "vendor_id", "customer_id"}

    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", False)
    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert set(scope.keys()) == {"forwarder_id"}


def test_role_scope_audit_log_switch_emits_decision_log(
    db_session,
    monkeypatch,
    caplog,
):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_AUDIT_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_AUDIT_VERBOSE", False)
    monkeypatch.setattr(settings, "ROLE_SCOPE_AUDIT_SAMPLE_RATE", 1.0)

    with caplog.at_level("INFO"):
        resolve_scope_by_field(
            db_session,
            user_email="multi@example.com",
            endpoint_key="purchase_orders",
        )

    assert any(
        "role_scope_decision endpoint=purchase_orders" in record.message
        for record in caplog.records
    )


def test_role_scope_union_metadata_default_policy_matches_union(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert set(scope.keys()) == {"forwarder_id", "vendor_id", "customer_id"}
    assert scope["forwarder_id"] == {11}
    assert scope["vendor_id"] == {21}
    assert scope["customer_id"] == {31}


def test_role_scope_union_metadata_uses_readable_identifier_filters(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    custom_metadata = {
        "version": "1.0",
        "endpoint_policies": [
            {
                "endpoint": "purchase_orders",
                "enabled": True,
                "source_filter": {
                    "operator": "any_of",
                    "clauses": [
                        {
                            "dimension": "supplier_code",
                            "target_field": "vendor_id",
                            "include_values": ["SU-0021"],
                        }
                    ],
                },
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.role_scope_metadata_service.get_role_scope_metadata",
        lambda: custom_metadata,
    )

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
    )
    assert scope == {"vendor_id": {21}}


def test_role_scope_union_metadata_rollout_untargeted_endpoint_stays_legacy(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "purchase_orders")

    shipments_scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="shipments.from_schedule_lines",
    )
    assert set(shipments_scope.keys()) == {"forwarder_id"}


def test_role_scope_union_metadata_no_policy_can_fallback_to_union(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    custom_metadata = {
        "version": "1.0",
        "endpoint_policies": [
            {
                "endpoint": "some.other.endpoint",
                "enabled": True,
                "source_filter": {
                    "operator": "any_of",
                    "clauses": [{"dimension": "supplier_code", "target_field": "vendor_id"}],
                },
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.role_scope_metadata_service.get_role_scope_metadata",
        lambda: custom_metadata,
    )

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    no_fallback_scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
    )
    assert no_fallback_scope == {}

    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", True)
    fallback_scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="purchase_orders",
    )
    assert set(fallback_scope.keys()) == {"forwarder_id", "vendor_id", "customer_id"}


def test_role_scope_union_metadata_path_and_method_match_scope_dimensions(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key="shipments.from_schedule_lines",
        http_method="POST",
        endpoint_path="/api/v1/shipments/from_schedule_lines",
    )
    assert set(scope.keys()) == {"customer_id", "forwarder_id"}
    assert scope["customer_id"] == {31}
    assert scope["forwarder_id"] == {11}


def test_role_scope_union_metadata_disallowed_roles_are_denied(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="viewer@example.com",
        endpoint_key="shipments.from_schedule_lines",
        http_method="POST",
        endpoint_path="/api/v1/shipments/from-schedule-lines",
    )
    assert is_scope_denied(scope)


def test_role_scope_union_metadata_bypass_role_is_unscoped(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="admin@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert not is_scope_denied(scope)
    assert scope == {}


@pytest.mark.parametrize(
    ("method", "path", "expected_keys"),
    [
        (
            "GET",
            "/api/v1/purchase-orders/initialization-data",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "POST",
            "/api/v1/purchase-orders/schedule-lines/merge",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "GET",
            "/api/v1/shipments",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "GET",
            "/api/v1/shipments/workspace/101",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "GET",
            "/api/v1/shipments/101",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "DELETE",
            "/api/v1/shipments/101",
            {"customer_id", "forwarder_id"},
        ),
        (
            "GET",
            "/api/v1/reports/po_to_group/metadata",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
        (
            "GET",
            "/api/v1/reports/visibility/metadata",
            {"customer_id", "vendor_id", "forwarder_id"},
        ),
    ],
)
def test_role_scope_union_metadata_new_policy_paths_resolve_expected_scope(
    db_session,
    monkeypatch,
    method: str,
    path: str,
    expected_keys: set[str],
):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    scope = resolve_scope_by_field(
        db_session,
        user_email="multi@example.com",
        endpoint_key=None,
        http_method=method,
        endpoint_path=path,
    )
    assert not is_scope_denied(scope)
    assert set(scope.keys()) == expected_keys


def test_role_scope_union_metadata_admin_governance_paths_gate_roles(db_session, monkeypatch):
    _seed_scope_matrix(db_session)

    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    denied_scope = resolve_scope_by_field(
        db_session,
        user_email="viewer@example.com",
        endpoint_key=None,
        http_method="GET",
        endpoint_path="/users",
    )
    assert is_scope_denied(denied_scope)

    admin_scope = resolve_scope_by_field(
        db_session,
        user_email="admin@example.com",
        endpoint_key=None,
        http_method="GET",
        endpoint_path="/users",
    )
    assert not is_scope_denied(admin_scope)
    assert admin_scope == {}
