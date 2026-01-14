from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.domains import DuplicateError, create_domain, delete_domain, get_domain, list_domains, update_domain
from app.db.session import get_db
from app.schemas.domains import DomainCreate, DomainOut, DomainUpdate

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("", response_model=DomainOut, status_code=status.HTTP_201_CREATED)
def create_domain_api(payload: DomainCreate, db: Session = Depends(get_db)):
    try:
        return create_domain(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{domain_id}", response_model=DomainOut)
def get_domain_api(domain_id: int, db: Session = Depends(get_db)):
    obj = get_domain(db, domain_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Domain not found")
    return obj


@router.get("", response_model=list[DomainOut])
def list_domains_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    domain_name: str | None = Query(None),
    technical_key: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_domains(
        db,
        skip=skip,
        limit=limit,
        domain_name=domain_name,
        technical_key=technical_key,
        is_active=is_active,
    )


@router.patch("/{domain_id}", response_model=DomainOut)
def update_domain_api(domain_id: int, payload: DomainUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_domain(db, domain_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Domain not found")
    return obj


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain_api(domain_id: int, db: Session = Depends(get_db)):
    ok = delete_domain(db, domain_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Domain not found")
    return None
