from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.partner_master import PartnerMaster
from app.models.masteraddr import MasterAddr
from app.schemas.partner_composite import PartnerFullSchema
from app.services.number_range_get import NumberRangeService


class PartnerService:
    @staticmethod
    def upsert_partner_full_record(
        db: Session,
        payload: PartnerFullSchema,
        current_user_email: str,
        current_user_tz: str | None = None,
    ) -> PartnerMaster:
        try:
            with db.begin():
                partner_data = payload.partner.model_dump(by_alias=True)
                address_data = payload.address.model_dump()
                sanitized_address_data = {
                    k: v
                    for k, v in address_data.items()
                    if k
                    not in {
                        "created_by",
                        "last_changed_by",
                        "valid_from",
                        "timezone",
                    }
                }

                partner_obj = None
                if payload.is_edit_mode:
                    partner_id = partner_data.get("id")
                    if not partner_id:
                        raise HTTPException(status_code=400, detail="Partner ID required for edit")
                    partner_obj = db.get(PartnerMaster, partner_id)
                    if not partner_obj:
                        raise HTTPException(status_code=404, detail="Partner not found")

                # Step A: Address
                if partner_obj and partner_obj.addr_id:
                    address_obj = db.get(MasterAddr, partner_obj.addr_id)
                    if not address_obj:
                        address_obj = MasterAddr(**sanitized_address_data)
                        address_obj.valid_from = datetime.utcnow().date()
                        address_obj.valid_to = address_data.get("valid_to") or date(9999, 12, 31)
                        address_obj.timezone = current_user_tz
                        address_obj.created_by = current_user_email
                        address_obj.last_changed_by = current_user_email
                        db.add(address_obj)
                        db.flush()
                    else:
                        for k, v in sanitized_address_data.items():
                            if v is None and not isinstance(v, bool):
                                continue
                            setattr(address_obj, k, v)
                        if address_data.get("valid_to") is not None:
                            address_obj.valid_to = address_data.get("valid_to")
                        if current_user_tz:
                            address_obj.timezone = current_user_tz
                        address_obj.last_changed_by = current_user_email
                else:
                    address_obj = MasterAddr(**sanitized_address_data)
                    address_obj.valid_from = datetime.utcnow().date()
                    address_obj.valid_to = address_data.get("valid_to") or date(9999, 12, 31)
                    address_obj.timezone = current_user_tz
                    address_obj.created_by = current_user_email
                    address_obj.last_changed_by = current_user_email
                    db.add(address_obj)
                    db.flush()

                # Step B: Number range (create only) if identifier not supplied
                if not payload.is_edit_mode and not partner_data.get("partner_identifier"):
                    role_id = partner_data.get("partner_role")
                    if not role_id:
                        raise HTTPException(status_code=400, detail="partner_role is required")
                    partner_code = NumberRangeService.get_next_number(db, "PARTNER", role_id)
                else:
                    partner_code = partner_data.get("partner_identifier")

                # Step C: Partner
                if payload.is_edit_mode:
                    for k, v in partner_data.items():
                        if k in ("id", "partner_identifier"):
                            continue
                        if v is None and not isinstance(v, bool):
                            continue
                        if k == "partner_role":
                            setattr(partner_obj, "role_id", v)
                        else:
                            setattr(partner_obj, k, v)
                    partner_obj.addr_id = address_obj.id
                else:
                    partner_obj = PartnerMaster(
                        partner_identifier=partner_code,
                        role_id=partner_data["partner_role"],
                        legal_name=partner_data["legal_name"],
                        trade_name=partner_data.get("trade_name"),
                        tax_registration_id=partner_data.get("tax_registration_id"),
                        payment_terms_code=partner_data.get("payment_terms_code"),
                        preferred_currency=partner_data.get("preferred_currency", "USD"),
                        is_active=partner_data.get("is_active", True),
                        is_verified=partner_data.get("is_verified", False),
                        addr_id=address_obj.id,
                    )
                    db.add(partner_obj)
                    db.flush()

                return partner_obj
        except ValueError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate value violates unique constraint: {e.orig}",
            ) from e

    @staticmethod
    def get_partner_full_record(db: Session, partner_id: int) -> PartnerMaster | None:
        return (
            db.query(PartnerMaster)
            .options(joinedload(PartnerMaster.address))
            .filter(PartnerMaster.id == partner_id)
            .first()
        )
