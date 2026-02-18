from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.company_master import CompanyMaster
from app.models.customer_master import CustomerMaster
from app.models.customer_role import CustomerRole
from app.models.roles import Role
from app.models.user_customer_link import UserCustomerLink
from app.models.user_roles import UserRole
from app.models.users import User
from app.services.metadata_framework_service import MetadataFrameworkService
from app.services.role_scope_metadata_service import resolve_metadata_scope_decision
from app.services.role_scope_policy import (
    is_scope_denied,
    resolve_scope_by_field,
    scope_deny_detail,
)
from app.services.role_scope_policy_validator import (
    validate_role_scope_policy_payload,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_validator_rejects_incompatible_source_dimension_pair():
    payload = {
        "endpoint_policies": [
            {
                "id": "POL-X",
                "endpoint": "purchase_orders",
                "enabled": True,
                "scope_mode": "union",
                "allowed_roles_any": ["USER_PURCH_BUYER"],
                "scope_dimensions": ["company_id"],
            }
        ],
        "role_scope_mapping": [
            {
                "role": "USER_PURCH_BUYER",
                "dimension": "company_id",
                "source": "user_customer_link.customer_id",
            }
        ],
    }
    issues = validate_role_scope_policy_payload(payload, required_endpoint_keys=None)
    assert any("incompatible source/dimension pair" in issue for issue in issues)


def test_validator_requires_resolvable_scoped_policy():
    payload = {
        "endpoint_policies": [
            {
                "id": "POL-X",
                "endpoint": "purchase_orders",
                "enabled": True,
                "scope_mode": "union",
                "allowed_roles_any": ["SUPPLIER"],
                "scope_dimensions": ["customer_id"],
            }
        ],
        "role_scope_mapping": [
            {
                "role": "SUPPLIER",
                "dimension": "vendor_id",
                "source": "user_partner_link.partner_id where partner_role=SUPPLIER",
            }
        ],
    }
    issues = validate_role_scope_policy_payload(payload, required_endpoint_keys=None)
    assert any("no allowed role can resolve" in issue for issue in issues)


def test_validator_requires_business_endpoint_coverage():
    payload = {"endpoint_policies": [], "role_scope_mapping": []}
    issues = validate_role_scope_policy_payload(payload)
    assert any("Missing required endpoint policies" in issue for issue in issues)


def test_validator_accepts_default_policy_file():
    default_path = _repo_root() / "app" / "core" / "decision" / "role_scope_policy.default.json"
    payload = json.loads(default_path.read_text(encoding="utf-8"))
    issues = validate_role_scope_policy_payload(payload)
    assert issues == []


def test_publish_blocks_invalid_role_scope_policy_payload(db_session):
    MetadataFrameworkService.ensure_type(
        db_session,
        type_key="role_scope_policy",
        display_name="Role Scope Policy",
        description="Policy",
    )
    draft = MetadataFrameworkService.save_draft(
        db_session,
        type_key="role_scope_policy",
        payload={
            "endpoint_policies": [
                {
                    "id": "POL-X",
                    "endpoint": "purchase_orders",
                    "enabled": True,
                    "scope_mode": "union",
                    "allowed_roles_any": ["USER_PURCH_BUYER"],
                    "scope_dimensions": ["company_id"],
                }
            ],
            "role_scope_mapping": [
                {
                    "role": "USER_PURCH_BUYER",
                    "dimension": "company_id",
                    "source": "user_customer_link.customer_id",
                }
            ],
        },
        actor_email="tester@example.com",
    )

    with pytest.raises(HTTPException) as exc:
        MetadataFrameworkService.publish(
            db_session,
            type_key="role_scope_policy",
            actor_email="tester@example.com",
            version_no=draft.version_no,
        )

    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "Role scope policy validation failed."


def test_metadata_scope_resolves_company_ids_from_user_customer_links(db_session, monkeypatch):
    db_session.add(Role(id=1, name="USER_PURCH_BUYER"))
    db_session.add(
        User(
            id=1,
            username="buyer",
            email="buyer@example.com",
            is_active=True,
            clearance=0,
        )
    )
    db_session.flush()
    db_session.add(UserRole(user_id=1, role_id=1))
    db_session.add(CustomerRole(id=1, role_code="B2B", role_name="B2B", is_active=True))
    db_session.add(
        CompanyMaster(
            id=101,
            company_code="COMP-101",
            branch_code="HQ",
            legal_name="Company 101",
            tax_id="TAX-101",
            default_currency="USD",
            is_active=True,
        )
    )
    db_session.add(
        CustomerMaster(
            id=201,
            customer_identifier="CUST-201",
            role_id=1,
            company_id=101,
            legal_name="Customer 201",
            preferred_currency="USD",
            is_active=True,
            is_verified=True,
            created_by="seed@local",
            last_changed_by="seed@local",
        )
    )
    db_session.add(
        UserCustomerLink(
            user_email="buyer@example.com",
            customer_id=201,
            deletion_indicator=False,
        )
    )
    db_session.commit()

    metadata = {
        "endpoint_policies": [
            {
                "id": "POL-COMPANY",
                "endpoint": "purchase_orders",
                "enabled": True,
                "scope_mode": "union",
                "allowed_roles_any": ["USER_PURCH_BUYER"],
                "scope_dimensions": ["company_id"],
            }
        ],
        "role_scope_mapping": [
            {
                "role": "USER_PURCH_BUYER",
                "dimension": "company_id",
                "source": "user_customer_link.company_id",
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.role_scope_metadata_service.get_role_scope_metadata",
        lambda: metadata,
    )

    decision = resolve_metadata_scope_decision(
        db_session,
        user_email="buyer@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )

    assert decision.allow is True
    assert decision.scope_by_field == {"company_id": {101}}


def test_metadata_scope_denies_empty_resolved_scope_for_scoped_policy(
    db_session,
    monkeypatch,
):
    db_session.add(Role(id=1, name="USER_PURCH_BUYER"))
    db_session.add(
        User(
            id=1,
            username="buyer",
            email="buyer@example.com",
            is_active=True,
            clearance=0,
        )
    )
    db_session.flush()
    db_session.add(UserRole(user_id=1, role_id=1))
    db_session.commit()

    metadata = {
        "endpoint_policies": [
            {
                "id": "POL-CUST",
                "endpoint": "purchase_orders",
                "enabled": True,
                "scope_mode": "union",
                "allowed_roles_any": ["USER_PURCH_BUYER"],
                "scope_dimensions": ["customer_id"],
            }
        ],
        "role_scope_mapping": [
            {
                "role": "USER_PURCH_BUYER",
                "dimension": "customer_id",
                "source": "user_customer_link.customer_id",
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.role_scope_metadata_service.get_role_scope_metadata",
        lambda: metadata,
    )

    decision = resolve_metadata_scope_decision(
        db_session,
        user_email="buyer@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert decision.allow is False
    assert decision.reason == "empty_resolved_scope_for_scoped_endpoint"


def test_scope_deny_detail_reports_empty_resolved_scope_reason(db_session, monkeypatch):
    db_session.add(Role(id=1, name="USER_PURCH_BUYER"))
    db_session.add(
        User(
            id=1,
            username="buyer",
            email="buyer@example.com",
            is_active=True,
            clearance=0,
        )
    )
    db_session.flush()
    db_session.add(UserRole(user_id=1, role_id=1))
    db_session.commit()

    metadata = {
        "endpoint_policies": [
            {
                "id": "POL-CUST",
                "endpoint": "purchase_orders",
                "enabled": True,
                "scope_mode": "union",
                "allowed_roles_any": ["USER_PURCH_BUYER"],
                "scope_dimensions": ["customer_id"],
            }
        ],
        "role_scope_mapping": [
            {
                "role": "USER_PURCH_BUYER",
                "dimension": "customer_id",
                "source": "user_customer_link.customer_id",
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.role_scope_metadata_service.get_role_scope_metadata",
        lambda: metadata,
    )
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", True)
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_MODE", "union_metadata")
    monkeypatch.setattr(settings, "ROLE_SCOPE_ROLLOUT_ENDPOINTS", "")
    monkeypatch.setattr(settings, "ROLE_SCOPE_METADATA_FALLBACK_TO_UNION", False)

    raw_scope = resolve_scope_by_field(
        db_session,
        user_email="buyer@example.com",
        endpoint_key="purchase_orders",
        http_method="GET",
        endpoint_path="/api/v1/purchase-orders",
    )
    assert is_scope_denied(raw_scope)
    assert (
        scope_deny_detail(raw_scope)
        == "Access denied by role-scope policy: empty resolved scope for scoped endpoint"
    )
