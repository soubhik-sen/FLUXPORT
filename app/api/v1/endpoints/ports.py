from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.crud.forwarder_port import list_ports_for_forwarder
from app.db.session import get_db
from app.models.logistics_lookups import PortLookup

router = APIRouter()


@router.get("")
def list_ports(
    forwarder_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    if forwarder_id is None:
        return []
    ports = list_ports_for_forwarder(db, forwarder_id)
    return [
        {
            "id": p.id,
            "code": p.port_code,
            "name": p.port_name,
            "country": p.country,
            "label": f"{p.port_code} - {p.port_name} ({p.country})",
        }
        for p in ports
    ]


@router.get("/search")
def search_ports(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    like = f"%{q}%"
    stmt = (
        select(PortLookup)
        .where(
            or_(
                PortLookup.port_code.ilike(like),
                PortLookup.port_name.ilike(like),
                PortLookup.country.ilike(like),
            ),
            PortLookup.is_active == True,  # noqa: E712
        )
        .order_by(PortLookup.port_code.asc())
        .limit(20)
    )
    ports = db.execute(stmt).scalars().all()
    return [
        {
            "id": p.id,
            "code": p.port_code,
            "name": p.port_name,
            "country": p.country,
            "label": f"{p.port_code} - {p.port_name} ({p.country})",
        }
        for p in ports
    ]
