from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.customer_master import CustomerMaster
from app.models.masteraddr import MasterAddr
from app.schemas.customer_composite import CustomerFullSchema, CustomerFullResponse
from app.services.number_range_get import NumberRangeService


class CustomerService:
    @staticmethod
    def upsert_customer_full_record(
        db: Session,
        payload: CustomerFullSchema,
        current_user_email: str,
        current_user_tz: str | None = None,
    ) -> CustomerMaster:
        try:
            with db.begin():
                customer_data = payload.customer.model_dump(by_alias=True)
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

                customer_obj = None
                if payload.is_edit_mode:
                    customer_id = customer_data.get("id")
                    if not customer_id:
                        raise HTTPException(status_code=400, detail="Customer ID required for edit")
                    customer_obj = db.get(CustomerMaster, customer_id)
                    if not customer_obj:
                        raise HTTPException(status_code=404, detail="Customer not found")

                # Step A: Address
                if customer_obj and customer_obj.addr_id:
                    address_obj = db.get(MasterAddr, customer_obj.addr_id)
                    if not address_obj:
                        address_obj = MasterAddr(**sanitized_address_data)
                        address_obj.valid_from = datetime.utcnow().date()
                        address_obj.valid_to = (
                            address_data.get("valid_to") or date(9999, 12, 31)
                        )
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

                # Step B: Number range (create only)
                if not payload.is_edit_mode:
                    role_id = customer_data.get("customer_group")
                    if not role_id:
                        raise HTTPException(status_code=400, detail="customer_group is required")
                    customer_code = NumberRangeService.get_next_number(db, "CUSTOMER", role_id)

                # Step C: Customer
                if payload.is_edit_mode:
                    for k, v in customer_data.items():
                        if k in ("id", "customer_identifier"):
                            continue
                        if v is None and not isinstance(v, bool):
                            continue
                        if k == "customer_group":
                            setattr(customer_obj, "role_id", v)
                        else:
                            setattr(customer_obj, k, v)
                    customer_obj.addr_id = address_obj.id
                    customer_obj.last_changed_by = current_user_email
                else:
                    customer_obj = CustomerMaster(
                        customer_identifier=customer_code,
                        role_id=customer_data["customer_group"],
                        legal_name=customer_data["legal_name"],
                        trade_name=customer_data.get("trade_name"),
                        tax_registration_id=customer_data.get("tax_registration_id"),
                        payment_terms_code=customer_data.get("payment_terms_code"),
                        preferred_currency=customer_data.get("preferred_currency", "USD"),
                        validity_to=customer_data.get("validity_to", date(9999, 12, 31)),
                        is_active=customer_data.get("is_active", True),
                        is_verified=customer_data.get("is_verified", False),
                        addr_id=address_obj.id,
                        created_by=current_user_email,
                        last_changed_by=current_user_email,
                    )
                    db.add(customer_obj)
                    db.flush()

                return customer_obj
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
    def get_customer_full_record(db: Session, customer_id: int) -> CustomerMaster | None:
        return (
            db.query(CustomerMaster)
            .options(joinedload(CustomerMaster.address))
            .filter(CustomerMaster.id == customer_id)
            .first()
        )
