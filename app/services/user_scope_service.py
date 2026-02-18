from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer_master import CustomerMaster
from app.models.partner_master import PartnerMaster
from app.models.partner_role import PartnerRole
from app.models.roles import Role
from app.models.user_customer_link import UserCustomerLink
from app.models.user_partner_link import UserPartnerLink
from app.models.user_roles import UserRole
from app.models.users import User

_FORWARDER_CODES = {"FO", "FORWARDER"}
_SUPPLIER_CODES = {"SU", "SUPPLIER"}


@dataclass
class UserUnionScope:
    role_names: set[str]
    forwarder_partner_ids: set[int]
    supplier_partner_ids: set[int]
    customer_ids: set[int]

    @property
    def has_any_scope(self) -> bool:
        return bool(
            self.forwarder_partner_ids
            or self.supplier_partner_ids
            or self.customer_ids
        )

    def field_to_ids(self) -> dict[str, set[int]]:
        mapping: dict[str, set[int]] = {}
        if self.forwarder_partner_ids:
            mapping["forwarder_id"] = set(self.forwarder_partner_ids)
        if self.supplier_partner_ids:
            mapping["vendor_id"] = set(self.supplier_partner_ids)
        if self.customer_ids:
            mapping["customer_id"] = set(self.customer_ids)
        return mapping


def list_user_roles(db: Session, user_id: int) -> list[Role]:
    stmt_roles = (
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.name.asc())
    )
    return list(db.execute(stmt_roles).scalars().all())


def list_user_customers(db: Session, user_email: str) -> list[dict]:
    stmt_user_customers = (
        select(UserCustomerLink)
        .where(UserCustomerLink.user_email == user_email)
        .where(UserCustomerLink.deletion_indicator == False)
    )
    user_customers = db.execute(stmt_user_customers).scalars().all()
    return [
        {
            "id": uc.customer_id,
            "name": uc.customer_name,
            "code": uc.customer.customer_identifier if uc.customer else None,
            "company_id": uc.customer.company_id if uc.customer else None,
            "company_name": (
                uc.customer.company.legal_name
                if uc.customer and uc.customer.company
                else None
            ),
        }
        for uc in user_customers
    ]


def list_user_partners(db: Session, user_email: str) -> list[dict]:
    stmt_user_partners = (
        select(UserPartnerLink)
        .where(UserPartnerLink.user_email == user_email)
        .where(UserPartnerLink.deletion_indicator == False)
    )
    user_partners = db.execute(stmt_user_partners).scalars().all()
    return [
        {
            "id": up.partner_id,
            "name": up.partner_name,
            "code": up.partner.partner_identifier if up.partner else None,
            "role_id": up.partner.role_id if up.partner else None,
            "role_code": up.partner.role.role_code if up.partner and up.partner.role else None,
            "role_name": up.partner.role.role_name if up.partner and up.partner.role else None,
        }
        for up in user_partners
    ]


def resolve_union_scope_ids(db: Session, user_email: str) -> UserUnionScope:
    role_rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(User, User.id == UserRole.user_id)
        .filter(User.email == user_email)
        .all()
    )
    role_names = {
        (row[0] or "").strip().upper() for row in role_rows if row and row[0]
    }

    partner_rows = (
        db.query(UserPartnerLink.partner_id, PartnerRole.role_code)
        .join(PartnerMaster, PartnerMaster.id == UserPartnerLink.partner_id)
        .join(PartnerRole, PartnerRole.id == PartnerMaster.role_id)
        .filter(UserPartnerLink.user_email == user_email)
        .filter(UserPartnerLink.deletion_indicator == False)
        .all()
    )

    forwarder_partner_ids: set[int] = set()
    supplier_partner_ids: set[int] = set()
    for partner_id, role_code in partner_rows:
        if partner_id is None:
            continue
        normalized = (role_code or "").strip().upper()
        if normalized in _FORWARDER_CODES:
            forwarder_partner_ids.add(int(partner_id))
        if normalized in _SUPPLIER_CODES:
            supplier_partner_ids.add(int(partner_id))

    customer_rows = (
        db.query(UserCustomerLink.customer_id)
        .join(CustomerMaster, CustomerMaster.id == UserCustomerLink.customer_id)
        .filter(UserCustomerLink.user_email == user_email)
        .filter(UserCustomerLink.deletion_indicator == False)
        .filter(CustomerMaster.is_active == True)
        .all()
    )
    customer_ids = {
        int(row[0]) for row in customer_rows if row and row[0] is not None
    }

    return UserUnionScope(
        role_names=role_names,
        forwarder_partner_ids=forwarder_partner_ids,
        supplier_partner_ids=supplier_partner_ids,
        customer_ids=customer_ids,
    )


def resolve_legacy_precedence_scope_ids(db: Session, user_email: str) -> dict[str, set[int]]:
    scope = resolve_union_scope_ids(db, user_email)
    if scope.forwarder_partner_ids:
        return {"forwarder_id": set(scope.forwarder_partner_ids)}
    if scope.supplier_partner_ids:
        return {"vendor_id": set(scope.supplier_partner_ids)}
    if scope.customer_ids:
        return {"customer_id": set(scope.customer_ids)}
    return {}
