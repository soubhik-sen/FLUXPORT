
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.customer_branch import (
    DuplicateError,
    create_customer_branch,
    delete_customer_branch,
    get_customer_branch,
    list_customer_branches,
    update_customer_branch,
)
from app.db.session import get_db
from app.schemas.customer_branch import CustomerBranchCreate, CustomerBranchOut, CustomerBranchUpdate

router = APIRouter(prefix="/customer-branches", tags=["customer-branches"])


@router.post("", response_model=CustomerBranchOut, status_code=status.HTTP_201_CREATED)
def create_customer_branch_api(payload: CustomerBranchCreate, db: Session = Depends(get_db)):
    try:
        return create_customer_branch(db, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{row_id}", response_model=CustomerBranchOut)
def get_customer_branch_api(row_id: int, db: Session = Depends(get_db)):
    obj = get_customer_branch(db, row_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer branch mapping not found")
    return obj


@router.get("", response_model=list[CustomerBranchOut])
def list_customer_branches_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    include_deleted: bool = Query(False),
    as_of: date | None = Query(None),
    customer_id: int | None = Query(None, ge=1),
    branch_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    return list_customer_branches(
        db,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        as_of=as_of,
        customer_id=customer_id,
        branch_id=branch_id,
    )


@router.patch("/{row_id}", response_model=CustomerBranchOut)
def update_customer_branch_api(row_id: int, payload: CustomerBranchUpdate, db: Session = Depends(get_db)):
    try:
        obj = update_customer_branch(db, row_id, payload)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if not obj:
        raise HTTPException(status_code=404, detail="Customer branch mapping not found")
    return obj


@router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_branch_api(
    row_id: int,
    mode: str = Query("soft", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    ok = delete_customer_branch(db, row_id, mode=mode)
    if not ok:
        raise HTTPException(status_code=404, detail="Customer branch mapping not found")
    return None
