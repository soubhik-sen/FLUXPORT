"""
Seed core lookup and workflow tables with provided reference data.

Tables seeded:
  - po_type_lookup
  - po_status_lookup
  - purchase_org_lookup
  - company_master (maps from "company_lookup")
  - partner_master (maps from "vendor_lookup")
  - sys_workflow_rules
  - sys_number_ranges

This script uses db.add_all() and db.commit() to persist data.
"""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.po_lookups import (
    PurchaseOrderStatusLookup,
    PurchaseOrderTypeLookup,
    PurchaseOrgLookup,
)
from app.models.company_master import CompanyMaster
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.roles import Role
from app.models.workflow_rules import SysWorkflowRule
from app.models.number_range import SysNumberRange


def _upsert_by_id(
    db: Session,
    model: Any,
    row_id: int,
    data: dict[str, Any],
    new_objects: list[Any],
) -> None:
    obj = db.get(model, row_id)
    if obj:
        for key, value in data.items():
            setattr(obj, key, value)
        return
    obj = model(id=row_id, **data)
    new_objects.append(obj)


def _ensure_roles(db: Session) -> None:
    # Roles required by sys_workflow_rules
    required_roles = [
        (1, "User"),
        (2, "Manager"),
        (3, "Warehouse"),
    ]
    new_objects: list[Any] = []
    for role_id, name in required_roles:
        _upsert_by_id(db, Role, role_id, {"name": name}, new_objects)
    if new_objects:
        db.add_all(new_objects)
        db.commit()


def _ensure_partner_role(db: Session) -> int:
    # Ensure a Supplier role exists for vendor_lookup mapping
    role = db.query(PartnerRole).filter(PartnerRole.role_code == "SUPPLIER").first()
    if role:
        return role.id

    role = PartnerRole(
        role_code="SUPPLIER",
        role_name="Supplier",
        description="External vendor/supplier",
        is_active=True,
    )
    db.add_all([role])
    db.commit()
    db.refresh(role)
    return role.id


def seed() -> None:
    db: Session = SessionLocal()
    try:
        _ensure_roles(db)
        supplier_role_id = _ensure_partner_role(db)

        new_objects: list[Any] = []

        # Purchase Order Types
        po_types = [
            {
                "id": 1,
                "type_code": "NP",
                "type_name": "Normal PO",
                "description": "Standard procurement of goods/services.",
                "is_active": True,
            },
            {
                "id": 2,
                "type_code": "ST",
                "type_name": "Stock Transfer",
                "description": "Internal transfer between warehouses/plants.",
                "is_active": True,
            },
        ]
        for row in po_types:
            _upsert_by_id(
                db,
                PurchaseOrderTypeLookup,
                row["id"],
                {
                    "type_code": row["type_code"],
                    "type_name": row["type_name"],
                    "description": row["description"],
                    "is_active": row["is_active"],
                },
                new_objects,
            )

        # Purchase Order Statuses
        po_statuses = [
            {
                "id": 1,
                "status_code": "DRAFT",
                "status_name": "Draft",
                "is_active": True,
            },
            {
                "id": 2,
                "status_code": "PENDING",
                "status_name": "Pending Approval",
                "is_active": True,
            },
            {
                "id": 3,
                "status_code": "OPEN",
                "status_name": "Open/Released",
                "is_active": True,
            },
            {
                "id": 4,
                "status_code": "CLOSED",
                "status_name": "Closed",
                "is_active": True,
            },
        ]
        for row in po_statuses:
            _upsert_by_id(
                db,
                PurchaseOrderStatusLookup,
                row["id"],
                {
                    "status_code": row["status_code"],
                    "status_name": row["status_name"],
                    "is_active": row["is_active"],
                },
                new_objects,
            )

        # Purchase Organizations
        purchase_orgs = [
            {"id": 1, "org_code": "P001", "org_name": "Central Procurement"},
            {"id": 2, "org_code": "P002", "org_name": "North America Sourcing"},
            {"id": 3, "org_code": "P003", "org_name": "EU Logistics Dept"},
        ]
        for row in purchase_orgs:
            _upsert_by_id(
                db,
                PurchaseOrgLookup,
                row["id"],
                {
                    "org_code": row["org_code"],
                    "org_name": row["org_name"],
                    "description": None,
                    "is_active": True,
                },
                new_objects,
            )

        # Company Lookup -> company_master
        companies = [
            {"id": 1, "company_code": "COMP01", "legal_name": "Global Tech Corp"},
            {"id": 2, "company_code": "COMP02", "legal_name": "Euro Logistics GmbH"},
            {"id": 3, "company_code": "COMP03", "legal_name": "Asia Pacific Ltd"},
        ]
        for row in companies:
            _upsert_by_id(
                db,
                CompanyMaster,
                row["id"],
                {
                    "company_code": row["company_code"],
                    "branch_code": "HQ",
                    "legal_name": row["legal_name"],
                    "trade_name": row["legal_name"],
                    "tax_id": f"TAX-{row['company_code']}",
                    "is_active": True,
                    "addr_id": None,
                    "default_currency": "USD",
                },
                new_objects,
            )

        # Vendor Lookup -> partner_master
        vendors = [
            {"id": 1, "partner_identifier": "VEND001", "legal_name": "Acme Industrial"},
            {"id": 2, "partner_identifier": "VEND002", "legal_name": "Global Supplies Inc"},
            {"id": 3, "partner_identifier": "VEND003", "legal_name": "FastShip Logistics"},
        ]
        for row in vendors:
            _upsert_by_id(
                db,
                PartnerMaster,
                row["id"],
                {
                    "partner_identifier": row["partner_identifier"],
                    "role_id": supplier_role_id,
                    "legal_name": row["legal_name"],
                    "trade_name": row["legal_name"],
                    "tax_registration_id": None,
                    "payment_terms_code": None,
                    "preferred_currency": "USD",
                    "is_active": True,
                    "is_verified": False,
                    "addr_id": None,
                },
                new_objects,
            )

        # Workflow Rules
        workflow_rules = [
            {
                "id": 1,
                "doc_category": "PO",
                "doc_type_id": 1,
                "state_code": "DRAFT",
                "action_key": "SUBMIT_FOR_APPROVAL",
                "required_role_id": 1,
                "is_blocking": False,
            },
            {
                "id": 2,
                "doc_category": "PO",
                "doc_type_id": 1,
                "state_code": "PENDING",
                "action_key": "APPROVE_PO",
                "required_role_id": 2,
                "is_blocking": True,
            },
            {
                "id": 3,
                "doc_category": "PO",
                "doc_type_id": 1,
                "state_code": "OPEN",
                "action_key": "RECEIVE_GOODS",
                "required_role_id": 3,
                "is_blocking": True,
            },
        ]
        for row in workflow_rules:
            _upsert_by_id(
                db,
                SysWorkflowRule,
                row["id"],
                {
                    "doc_category": row["doc_category"],
                    "doc_type_id": row["doc_type_id"],
                    "state_code": row["state_code"],
                    "action_key": row["action_key"],
                    "required_role_id": row["required_role_id"],
                    "is_blocking": row["is_blocking"],
                },
                new_objects,
            )

        # Number Ranges
        number_ranges = [
            {
                "id": 1,
                "doc_category": "PO",
                "doc_type_id": 1,
                "prefix": "NP-",
                "current_value": 1000,
                "padding": 6,
                "include_year": True,
                "is_active": True,
            },
            {
                "id": 2,
                "doc_category": "PO",
                "doc_type_id": 2,
                "prefix": "ST-",
                "current_value": 5000,
                "padding": 6,
                "include_year": False,
                "is_active": True,
            },
        ]
        for row in number_ranges:
            _upsert_by_id(
                db,
                SysNumberRange,
                row["id"],
                {
                    "doc_category": row["doc_category"],
                    "doc_type_id": row["doc_type_id"],
                    "prefix": row["prefix"],
                    "current_value": row["current_value"],
                    "padding": row["padding"],
                    "include_year": row["include_year"],
                    "is_active": row["is_active"],
                },
                new_objects,
            )

        if new_objects:
            db.add_all(new_objects)
        db.commit()
        print("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
