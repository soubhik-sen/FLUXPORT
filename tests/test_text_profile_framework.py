from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.api.v1.endpoints import purchase_orders as po_endpoints
from app.core.config import settings
from app.models.company_master import CompanyMaster
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.po_lookups import (
    PurchaseOrderItemStatusLookup,
    PurchaseOrderStatusLookup,
    PurchaseOrderTypeLookup,
    PurchaseOrgLookup,
)
from app.models.product_lookups import ProductTypeLookup, UomLookup
from app.models.product_master import ProductMaster
from app.models.purchase_order import PurchaseOrderHeader
from app.models.text_lookups import TextTypeLookup
from app.models.text_profile import POText, ProfileTextMap, ProfileTextValue, TextProfile, TextProfileRule
from app.models.user_attributes import UserAttribute
from app.models.user_countries import UserCountry
from app.models.users import User
from app.services.text_profile_service import TextProfileService


@pytest.fixture(autouse=True)
def _default_text_profile_runtime(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_MODE", "legacy_header")
    monkeypatch.setattr(settings, "ROLE_SCOPE_POLICY_ENABLED", False)
    monkeypatch.setattr(settings, "UNION_SCOPE_ENABLED", False)
    monkeypatch.setattr(settings, "TEXT_PROFILE_ENABLED", True)
    monkeypatch.setattr(settings, "TEXT_PROFILE_RESOLVE_MODE", "db_only")
    monkeypatch.setattr(settings, "TEXT_PROFILE_LEGACY_WORKSPACE_FALLBACK", True)


def _seed_po_basics(db):
    db.add_all(
        [
            PartnerRole(id=1, role_code="SU", role_name="Supplier", is_active=True),
            PartnerRole(id=2, role_code="FO", role_name="Forwarder", is_active=True),
        ]
    )
    db.flush()

    db.add_all(
        [
            PartnerMaster(
                id=101,
                partner_identifier="SU-0101",
                role_id=1,
                legal_name="Supplier 101",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            PartnerMaster(
                id=201,
                partner_identifier="FO-0201",
                role_id=2,
                legal_name="Forwarder 201",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
        ]
    )
    db.add(
        CompanyMaster(
            id=301,
            company_code="COMP-301",
            branch_code="HQ",
            legal_name="Company 301",
            tax_id="TAX-301",
            default_currency="USD",
            is_active=True,
        )
    )
    db.add_all(
        [
            PurchaseOrderTypeLookup(id=1, type_code="STD", type_name="Standard", is_active=True),
            PurchaseOrderStatusLookup(id=1, status_code="NEW", status_name="New", is_active=True),
            PurchaseOrgLookup(id=1, org_code="ORG", org_name="Main Org", is_active=True),
            PurchaseOrderItemStatusLookup(id=1, status_code="OPEN", status_name="Open", is_active=True),
            ProductTypeLookup(id=1, type_code="FG", type_name="Finished Good", is_active=True),
            UomLookup(id=1, uom_code="EA", uom_name="Each", uom_class="UNIT", is_active=True),
            ProductMaster(
                id=501,
                part_number="MAT-501",
                material_type_id=1,
                base_uom_id=1,
                short_description="Material 501",
                is_active=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            TextTypeLookup(id=1, text_type_code="GEN", text_type_name="General Text", is_active=True),
        ]
    )
    db.commit()


def _seed_text_profile(db, *, profile_id: int, version: int = 1, name: str | None = None) -> TextProfile:
    profile = TextProfile(
        id=profile_id,
        name=name or f"po_text_profile_{profile_id}",
        object_type="PO",
        profile_version=version,
        is_active=True,
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db.add(profile)
    db.flush()
    return profile


def test_text_profile_resolver_db_fallback_uses_locale_context(db_session):
    _seed_po_basics(db_session)
    db_session.add(
        User(
            id=1,
            username="localeuser",
            email="locale@example.com",
            clearance=0,
            is_active=True,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            UserCountry(user_id=1, country_code="BR"),
            UserAttribute(user_id=1, key="preferred_language", value="pt-BR"),
        ]
    )
    profile = TextProfile(
        id=1,
        name="po_text_profile",
        object_type="PO",
        profile_version=2,
        is_active=True,
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        TextProfileRule(
            object_type="PO",
            country_code="*",
            language="pt-BR",
            profile_id=profile.id,
            priority=1,
            is_active=True,
            created_by="seed@local",
            last_changed_by="seed@local",
        )
    )
    map_row = ProfileTextMap(
        profile_id=profile.id,
        text_type_id=1,
        sequence=10,
        is_mandatory=True,
        is_editable=True,
        is_active=True,
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db_session.add(map_row)
    db_session.flush()
    db_session.add_all(
        [
            ProfileTextValue(
                profile_text_map_id=map_row.id,
                language="en",
                country_code="*",
                text_value="Default EN",
                is_active=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            ProfileTextValue(
                profile_text_map_id=map_row.id,
                language="pt-BR",
                country_code="BR",
                text_value="Texto PT-BR",
                is_active=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
        ]
    )
    db_session.commit()

    resolved = TextProfileService.resolve_po_text_profile(
        db_session,
        user_email="locale@example.com",
        context={"type_id": 1, "company_id": 301, "vendor_id": 101, "forwarder_id": 201},
    )

    assert resolved.source == "db_fallback"
    assert resolved.profile_id == 1
    assert resolved.language == "pt-br"
    assert len(resolved.texts) == 1
    assert resolved.texts[0].text_value == "Texto PT-BR"


def test_po_create_persists_runtime_texts(client, db_session, monkeypatch):
    _seed_po_basics(db_session)
    _seed_text_profile(db_session, profile_id=11, version=3)
    db_session.commit()
    monkeypatch.setattr(po_endpoints, "_has_po_create_permission", lambda *_: True)

    payload = {
        "po_number": "PO-TEXT-001",
        "type_id": 1,
        "status_id": 1,
        "purchase_org_id": 1,
        "company_id": 301,
        "vendor_id": 101,
        "forwarder_id": 201,
        "order_date": "2026-02-15",
        "currency": "USD",
        "total_amount": "100.00",
        "created_by": "seed@local",
        "last_changed_by": "seed@local",
        "text_profile_id": 11,
        "text_profile_version": 3,
        "texts": [
            {
                "text_type_id": 1,
                "language": "en",
                "text_value": "Created runtime text",
            }
        ],
        "items": [
            {
                "item_number": 10,
                "product_id": 501,
                "status_id": 1,
                "quantity": "5.000",
                "unit_price": "20.00",
                "line_total": "100.00",
                "schedules": [],
            }
        ],
    }
    response = client.post(
        "/api/v1/purchase-orders/",
        headers={"X-User-Email": "creator@example.com"},
        json=payload,
    )
    assert response.status_code == 201
    created = response.json()
    po_id = int(created["id"])

    rows = db_session.query(POText).filter(POText.po_header_id == po_id).all()
    assert len(rows) == 1
    assert rows[0].text_value == "Created runtime text"
    assert rows[0].profile_id == 11
    assert rows[0].profile_version == 3


def test_po_workspace_reads_runtime_texts_and_update_endpoint(client, db_session):
    _seed_po_basics(db_session)
    _seed_text_profile(db_session, profile_id=77, version=2)
    db_session.commit()
    header = PurchaseOrderHeader(
        id=901,
        po_number="PO-WS-901",
        type_id=1,
        status_id=1,
        purchase_org_id=1,
        company_id=301,
        vendor_id=101,
        forwarder_id=201,
        order_date=date(2026, 2, 15),
        currency="USD",
        total_amount=Decimal("12.00"),
        created_by="seed@local",
        last_changed_by="seed@local",
    )
    db_session.add(header)
    db_session.flush()
    db_session.add(
        POText(
            po_header_id=header.id,
            profile_id=77,
            profile_version=2,
            text_type_id=1,
            language="en",
            text_value="Initial runtime text",
            is_user_edited=False,
            created_by="seed@local",
            last_changed_by="seed@local",
        )
    )
    db_session.commit()

    ws = client.get(
        "/api/v1/purchase-orders/workspace/901",
        headers={"X-User-Email": "editor@example.com"},
    )
    assert ws.status_code == 200
    payload = ws.json()
    assert payload["texts"]
    assert payload["texts"][0]["source"] == "po_text"
    assert payload["texts"][0]["text_value"] == "Initial runtime text"

    save_resp = client.put(
        "/api/v1/purchase-orders/901/texts",
        headers={"X-User-Email": "editor@example.com"},
        json={
            "profile_id": 77,
            "profile_version": 2,
            "texts": [
                {
                    "text_type_id": 1,
                    "language": "en",
                    "text_value": "Edited runtime text",
                }
            ],
        },
    )
    assert save_resp.status_code == 200

    updated = db_session.query(POText).filter(POText.po_header_id == 901).first()
    assert updated is not None
    assert updated.text_value == "Edited runtime text"
    assert updated.is_user_edited is True
