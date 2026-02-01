from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.users import User
from app.models.user_roles import UserRole
from app.models.roles import Role
from app.models.role_permissions import RolePermission
from app.models.permissions import Permission
from app.models.user_departments import UserDepartment
from app.models.user_countries import UserCountry
from app.models.user_attributes import UserAttribute
from app.models.user_customer_link import UserCustomerLink
from app.models.user_partner_link import UserPartnerLink

router = APIRouter(prefix="/user-profile", tags=["user-profile"])


@router.get("")
def get_user_profile(
    username: str = Query(None, min_length=1),
    email: str | None = Query(None, min_length=3),
    include_inactive_user: bool = Query(False),
    db: Session = Depends(get_db),
):
    if not username and not email:
        raise HTTPException(status_code=400, detail="Provide username or email")
    # 1) user
    if email:
        stmt_user = select(User).where(User.email == email)
    else:
        stmt_user = select(User).where(User.username == username)

    user = db.execute(stmt_user).scalar_one_or_none()



    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if (not include_inactive_user) and (not user.is_active):
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id

    # 2) roles
    stmt_roles = (
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.name.asc())
    )
    roles = list(db.execute(stmt_roles).scalars().all())

    # 3) role -> permissions (via role_permissions)
    role_ids = [r.id for r in roles]
    permissions = []
    if role_ids:
        stmt_perms = (
            select(Permission, RolePermission.role_id, RolePermission.role_name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
            .order_by(RolePermission.role_id.asc(), Permission.object_type.asc(), Permission.action_key.asc())
        )
        rows = db.execute(stmt_perms).all()
        for perm, role_id, role_name in rows:
            permissions.append(
                {
                    "role_id": role_id,
                    "role_name": role_name,
                    "permission": {
                        "id": perm.id,
                        "object_type": perm.object_type,
                        "action_key": perm.action_key,
                    },
                }
            )

    # 4) departments
    stmt_depts = select(UserDepartment).where(UserDepartment.user_id == user_id).order_by(UserDepartment.department.asc())
    departments = [r.department for r in db.execute(stmt_depts).scalars().all()]

    # 5) countries
    stmt_countries = select(UserCountry).where(UserCountry.user_id == user_id).order_by(UserCountry.country_code.asc())
    countries = [r.country_code for r in db.execute(stmt_countries).scalars().all()]

    # 6) attributes (key-value)
    stmt_attrs = select(UserAttribute).where(UserAttribute.user_id == user_id).order_by(UserAttribute.key.asc())
    attrs_rows = db.execute(stmt_attrs).scalars().all()
    attributes = [{"key": r.key, "value": r.value} for r in attrs_rows]


    # 7) customer links
    stmt_user_customers = (
        select(UserCustomerLink)
        .where(UserCustomerLink.user_email == user.email)
        .where(UserCustomerLink.deletion_indicator == False)
    )
    user_customers = db.execute(stmt_user_customers).scalars().all()
    customers = [
        {
            "id": uc.customer_id,
            "name": uc.customer_name,
            "code": uc.customer.customer_identifier if uc.customer else None,
        }
        for uc in user_customers
    ]

    # 8) partner links
    stmt_user_partners = (
        select(UserPartnerLink)
        .where(UserPartnerLink.user_email == user.email)
        .where(UserPartnerLink.deletion_indicator == False)
    )
    user_partners = db.execute(stmt_user_partners).scalars().all()
    partners = [
        {
            "id": up.partner_id,
            "name": up.partner_name,
            "code": up.partner.partner_identifier if up.partner else None,
        }
        for up in user_partners
    ]

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "clearance": user.clearance,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        },
        "departments": departments,
        "countries": countries,
        "attributes": attributes,
        "roles": [{"id": r.id, "name": r.name} for r in roles],
        "permissions_by_role": permissions,
        "customers": customers,
        "partners": partners,
    }
