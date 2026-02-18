from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps.request_identity import get_request_email
from app.db.session import get_db
from app.schemas.partner_composite import PartnerFullSchema, PartnerFullResponse
from app.services.partner_service import PartnerService

router = APIRouter()


def _get_user_email(request: Request) -> str:
    return get_request_email(request)


def _get_user_timezone(request: Request) -> str | None:
    return (
        request.headers.get("X-User-Timezone")
        or request.headers.get("X-Timezone")
        or request.headers.get("Timezone")
    )


@router.post(
    "/",
    response_model=PartnerFullResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Partner + Address",
)
def upsert_partner(
    payload: PartnerFullSchema,
    request: Request,
    db: Session = Depends(get_db),
):
    user_email = _get_user_email(request)
    user_tz = _get_user_timezone(request)
    partner_obj = PartnerService.upsert_partner_full_record(
        db=db,
        payload=payload,
        current_user_email=user_email,
        current_user_tz=user_tz,
    )

    address_obj = partner_obj.address
    return {
        "partner": partner_obj,
        "address": address_obj,
    }


@router.get(
    "/{partner_id}",
    response_model=PartnerFullResponse,
    summary="Get Partner + Address",
)
def get_partner(partner_id: int, db: Session = Depends(get_db)):
    partner_obj = PartnerService.get_partner_full_record(db, partner_id)
    if not partner_obj:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {
        "partner": partner_obj,
        "address": partner_obj.address,
    }


@router.get(
    "/batch/{partner_ids}",
    response_model=list[PartnerFullResponse],
    summary="Get multiple partners + addresses by IDs",
)
def get_partners_batch(partner_ids: str, db: Session = Depends(get_db)):
    tokens = [token.strip() for token in partner_ids.split(",")]
    ids: list[int] = []
    for token in tokens:
        if not token:
            continue
        try:
            ids.append(int(token))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid partner_id value: '{token}'",
            )
    if not ids:
        raise HTTPException(status_code=400, detail="At least one partner_id is required")
    records = PartnerService.get_partner_full_records(db, ids)
    id_to_record = {record.id: record for record in records}
    ordered = []
    for requested in ids:
        record = id_to_record.get(requested)
        if record:
            ordered.append({"partner": record, "address": record.address})
    return ordered
