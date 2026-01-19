from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.schemas.purchase_order import POHeaderCreate

def create_po_full(db: Session, po_in: POHeaderCreate):
    """
    Fully featured PO creation with error handling and validation.
    """
    try:
        # 1. Validation: Check if Vendor exists before trying to insert
        # vendor = db.query(PartnerMaster).filter(PartnerMaster.id == po_in.vendor_id).first()
        # if not vendor:
        #     raise HTTPException(status_code=404, detail="Vendor not found")

        # 2. Header Insertion
        header_data = po_in.model_dump(exclude={'items'})
        db_po = PurchaseOrderHeader(**header_data)
        db.add(db_po)
        db.flush() 

        # 3. Item Insertion with Calculation Validation
        for item_in in po_in.items:
            # Business Rule: Line Total must match Qty * Price
            expected_total = item_in.quantity * item_in.unit_price
            if abs(item_in.line_total - expected_total) > 0.01:
                raise HTTPException(status_code=400, detail=f"Line total mismatch for item {item_in.item_number}")

            db_item = PurchaseOrderItem(**item_in.model_dump(), po_header_id=db_po.id)
            db.add(db_item)

        db.commit()
        db.refresh(db_po)
        return db_po

    except IntegrityError as e:
        db.rollback()
        if "unique constraint" in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="PO Number already exists")
        raise HTTPException(status_code=400, detail="Database integrity error")
    except Exception as e:
        db.rollback()
        raise e