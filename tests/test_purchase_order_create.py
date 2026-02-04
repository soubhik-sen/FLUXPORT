from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest

from app.models.po_lookups import (
    PurchaseOrderStatusLookup,
    PurchaseOrderTypeLookup,
    PurchaseOrgLookup,
    PurchaseOrderItemStatusLookup,
)
from app.models.product_lookups import ProductTypeLookup, UomLookup
from app.models.product_master import ProductMaster
from app.models.customer_role import CustomerRole
from app.models.customer_master import CustomerMaster
from app.models.partner_role import PartnerRole
from app.models.partner_master import PartnerMaster
from app.models.company_master import CompanyMaster
from app.models.po_schedule_line import POScheduleLine


def _seed_minimal(db):
    # Lookups
    db.add_all(
        [
            PurchaseOrderTypeLookup(
                id=1, type_code="STD", type_name="Standard", is_active=True
            ),
            PurchaseOrderStatusLookup(
                id=1, status_code="NEW", status_name="New", is_active=True
            ),
            PurchaseOrgLookup(id=1, org_code="ORG", org_name="Org", is_active=True),
            PurchaseOrderItemStatusLookup(
                id=1, status_code="OPEN", status_name="Open", is_active=True
            ),
            ProductTypeLookup(id=1, type_code="GOODS", type_name="Goods", is_active=True),
            UomLookup(
                id=1, uom_code="EA", uom_name="Each", uom_class="Unit", is_active=True
            ),
        ]
    )

    # Roles
    db.add_all(
        [
            CustomerRole(id=1, role_code="B2B", role_name="B2B", is_active=True),
            PartnerRole(id=1, role_code="SUP", role_name="Supplier", is_active=True),
        ]
    )

    # Masters
    db.add_all(
        [
            CompanyMaster(
                id=1,
                company_code="COMP-1",
                branch_code="BR-1",
                legal_name="Company A",
                tax_id="TAX-0001",
                default_currency="USD",
                is_active=True,
            ),
            CustomerMaster(
                id=1,
                customer_identifier="CUST-0001",
                role_id=1,
                legal_name="Customer A",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
                created_by="seed@local",
                last_changed_by="seed@local",
            ),
            PartnerMaster(
                id=1,
                partner_identifier="VEN-0001",
                role_id=1,
                legal_name="Vendor A",
                preferred_currency="USD",
                is_active=True,
                is_verified=True,
            ),
            ProductMaster(
                id=1,
                sku_identifier="SKU-1",
                type_id=1,
                uom_id=1,
                short_description="Test Product",
                is_active=True,
            ),
        ]
    )
    db.commit()


def _base_payload():
    return {
        "po_number": "PO-TEST-0001",
        "type_id": 1,
        "status_id": 1,
        "purchase_org_id": 1,
        "company_id": 1,
        "vendor_id": 1,
        "order_date": "2025-01-01",
        "currency": "USD",
        "total_amount": 0,
        "created_by": "client@local",
        "last_changed_by": None,
        "items": [
            {
                "item_number": 10,
                "product_id": 1,
                "status_id": 1,
                "quantity": 5,
                "unit_price": 10,
                "line_total": 999,
                "schedules": [],
            }
        ],
    }


def test_create_po_minimal_success(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["po_number"] == "PO-TEST-0001"
    assert Decimal(str(data["total_amount"])) == Decimal("50")


def test_create_po_autonumber(monkeypatch, client, db_session):
    _seed_minimal(db_session)
    monkeypatch.setattr(
        "app.services.purchase_order_service.NumberRangeService.get_next_number",
        lambda *_args, **_kwargs: "PO-AUTO-0001",
    )
    payload = _base_payload()
    payload["po_number"] = ""
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["po_number"] == "PO-AUTO-0001"


def test_create_po_vendor_inactive(client, db_session):
    _seed_minimal(db_session)
    vendor = db_session.query(PartnerMaster).filter_by(id=1).first()
    vendor.is_active = False
    db_session.commit()
    payload = _base_payload()
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 400


def test_create_po_vendor_missing(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload["vendor_id"] = 999
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 400


def test_create_po_line_total_recalculated(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload["items"][0]["quantity"] = 3
    payload["items"][0]["unit_price"] = 7.5
    payload["items"][0]["line_total"] = 1
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 201, resp.text
    item = resp.json()["items"][0]
    assert Decimal(str(item["line_total"])) == Decimal("22.5")


def test_create_po_multiple_items_total(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload["items"].append(
        {
            "item_number": 20,
            "product_id": 1,
            "status_id": 1,
            "quantity": 2,
            "unit_price": 5,
            "line_total": 0,
            "schedules": [],
        }
    )
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 201, resp.text
    assert Decimal(str(resp.json()["total_amount"])) == Decimal("60")


def test_create_po_with_schedules_persists(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload["items"][0]["schedules"] = [
        {"schedule_number": 1, "quantity": 2, "delivery_date": "2025-01-10"},
        {"schedule_number": 2, "quantity": 3, "delivery_date": "2025-01-20"},
    ]
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 201, resp.text
    schedules = db_session.query(POScheduleLine).all()
    assert len(schedules) == 2


def test_create_po_duplicate_po_number(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    resp1 = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp1.status_code == 201, resp1.text
    resp2 = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp2.status_code == 409


def test_create_po_missing_required_header_field(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload.pop("type_id")
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 422


def test_create_po_schedule_missing_date_validation(client, db_session):
    _seed_minimal(db_session)
    payload = _base_payload()
    payload["items"][0]["schedules"] = [
        {"schedule_number": 1, "quantity": 2}
    ]
    resp = client.post("/api/v1/purchase-orders/", json=payload)
    assert resp.status_code == 422
