from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.customer_composite import CustomerFullSchema, CustomerFullResponse
from app.services.customer_service import CustomerService

router = APIRouter()


def _get_user_email(request: Request) -> str:
    return request.headers.get("X-User-Email") or request.headers.get("X-User") or "system@local"


def _get_user_timezone(request: Request) -> str | None:
    return (
        request.headers.get("X-User-Timezone")
        or request.headers.get("X-Timezone")
        or request.headers.get("Timezone")
    )


@router.post(
    "/",
    response_model=CustomerFullResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Customer + Address",
)
def upsert_customer(
    payload: CustomerFullSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    user_tz = _get_user_timezone(request)
    customer_obj = CustomerService.upsert_customer_full_record(
        db=db,
        payload=payload,
        current_user_email=user_email,
        current_user_tz=user_tz,
    )

    address_obj = customer_obj.address
    return {
        "customer": customer_obj,
        "address": address_obj,
    }


@router.get(
    "/{customer_id}",
    response_model=CustomerFullResponse,
    summary="Get Customer + Address",
)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer_obj = CustomerService.get_customer_full_record(db, customer_id)
    if not customer_obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "customer": customer_obj,
        "address": customer_obj.address,
    }
