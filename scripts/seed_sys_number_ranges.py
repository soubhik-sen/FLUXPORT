from app.db.session import SessionLocal
from app.models.number_range import SysNumberRange
from app.models.po_lookups import PurchaseOrderTypeLookup
from app.models.partner_role import PartnerRole
from app.models.customer_role import CustomerRole


def _ensure_range(db, category: str, type_id: int, prefix: str):
    existing = (
        db.query(SysNumberRange)
        .filter(SysNumberRange.doc_category == category)
        .filter(SysNumberRange.doc_type_id == type_id)
        .first()
    )
    if existing:
        return False
    db.add(
        SysNumberRange(
            doc_category=category,
            doc_type_id=type_id,
            prefix=prefix,
            current_value=0,
            padding=5,
            include_year=False,
            is_active=True,
        )
    )
    return True


def main():
    db = SessionLocal()
    try:
        created = 0

        po_types = (
            db.query(PurchaseOrderTypeLookup)
            .filter(PurchaseOrderTypeLookup.is_active == True)
            .all()
        )
        for t in po_types:
            code = (t.type_code or "PO").strip()
            if _ensure_range(db, "PO", t.id, f"{code}-"):
                created += 1

        partner_roles = (
            db.query(PartnerRole).filter(PartnerRole.is_active == True).all()
        )
        for r in partner_roles:
            code = (r.role_code or "PARTNER").strip()
            if _ensure_range(db, "PARTNER", r.id, f"{code}-"):
                created += 1

        customer_roles = (
            db.query(CustomerRole).filter(CustomerRole.is_active == True).all()
        )
        for r in customer_roles:
            code = (r.role_code or "CUSTOMER").strip()
            if _ensure_range(db, "CUSTOMER", r.id, f"{code}-"):
                created += 1

        db.commit()
        print(f"Seed complete. Added {created} ranges.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
