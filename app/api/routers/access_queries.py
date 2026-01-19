from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.permissions import Permission
from app.models.role_permissions import RolePermission
from app.models.roles import Role
from app.models.user_roles import UserRole
from app.models.users import User

router = APIRouter(prefix="/access-queries", tags=["access-queries"])


@router.get("/by-permission")
def by_permission(
    permission_id: int = Query(..., ge=1),
    include_inactive_users: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Input: permission_id
    Output: permission details + all roles that contain it + all users that have those roles
    """
    perm = db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    # roles containing this permission
    stmt_roles = (
        select(Role, RolePermission.role_name)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .where(RolePermission.permission_id == permission_id)
        .order_by(Role.name.asc())
    )
    role_rows = db.execute(stmt_roles).all()

    roles = [{"id": r.id, "name": r.name, "role_name": role_name} for (r, role_name) in role_rows]
    role_ids = [r["id"] for r in roles]

    # users having any of these roles
    users = []
    if role_ids:
        stmt_users = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(UserRole.role_id.in_(role_ids))
            .order_by(User.username.asc())
        )
        if not include_inactive_users:
            stmt_users = stmt_users.where(User.is_active.is_(True))

        user_rows = db.execute(stmt_users).scalars().all()

        # dedupe (in case user has multiple roles that match)
        seen = set()
        for u in user_rows:
            if u.id in seen:
                continue
            seen.add(u.id)
            users.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "clearance": u.clearance,
                    "is_active": u.is_active,
                }
            )

    return {
        "permission": {
            "id": perm.id,
            "object_type": perm.object_type,
            "action_key": perm.action_key,
        },
        "roles": roles,
        "users": users,
    }


@router.get("/by-role")
def by_role(
    role_id: int | None = Query(None, ge=1),
    role_name: str | None = Query(None),
    include_inactive_users: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Input: role_id or role_name (Role.name)
    Output: role details + all permissions in it + all users having that role
    """
    if role_id is None and (role_name is None or not role_name.strip()):
        raise HTTPException(status_code=400, detail="Provide role_id or role_name")

    # resolve role
    role = None
    if role_id is not None:
        role = db.get(Role, role_id)
    else:
        stmt = select(Role).where(Role.name == role_name.strip())
        role = db.execute(stmt).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # permissions in this role
    stmt_perms = (
        select(Permission, RolePermission.role_name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.object_type.asc(), Permission.action_key.asc())
    )
    perm_rows = db.execute(stmt_perms).all()

    permissions = []
    role_name_in_map = None
    for perm, rp_role_name in perm_rows:
        role_name_in_map = role_name_in_map or rp_role_name
        permissions.append(
            {
                "id": perm.id,
                "object_type": perm.object_type,
                "action_key": perm.action_key,
            }
        )

    # users having this role
    stmt_users = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role_id == role.id)
        .order_by(User.username.asc())
    )
    if not include_inactive_users:
        stmt_users = stmt_users.where(User.is_active.is_(True))

    users = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "clearance": u.clearance,
            "is_active": u.is_active,
        }
        for u in db.execute(stmt_users).scalars().all()
    ]

    return {
        "role": {
            "id": role.id,
            "name": role.name,
            "role_name": role_name_in_map,  # from mapping table if you use it
        },
        "permissions": permissions,
        "users": users,
    }
