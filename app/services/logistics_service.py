from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.shipment import ShipmentHeader, ShipmentItem
from app.models.purchase_order import PurchaseOrderItem
from app.schemas.shipment import ShipmentHeaderCreate

class LogisticsService:
    @staticmethod
    def create_shipment_with_validation(db: Session, shipment_in: ShipmentHeaderCreate):
        """
        Enterprise-grade Shipment creation:
        1. Atomic Transaction (All or nothing).
        2. Fulfillment Validation (Cannot ship more than ordered).
        3. Commercial Sync (Update PO Item statuses).
        """
        try:
            # 1. Start the Transaction
            # We use a context manager or the passed session
            
            # 2. Header Creation
            db_shipment = ShipmentHeader(
                shipment_number=shipment_in.shipment_number,
                status_id=shipment_in.status_id,
                mode_id=shipment_in.mode_id,
                carrier_id=shipment_in.carrier_id,
                estimated_departure=shipment_in.estimated_departure,
                estimated_arrival=shipment_in.estimated_arrival
            )
            db.add(db_shipment)
            db.flush() # Secure Shipment ID

            for item_in in shipment_in.items:
                # 3. Enterprise Guard: Fetch the associated PO Item
                po_item = db.query(PurchaseOrderItem).filter(
                    PurchaseOrderItem.id == item_in.po_item_id
                ).with_for_update().first() # Row-level lock for concurrency safety

                if not po_item:
                    raise HTTPException(status_code=404, detail=f"PO Item {item_in.po_item_id} not found")

                # 4. Fulfillment Logic: Validation
                # Calculate what has already been shipped across other shipments
                already_shipped = db.query(func.sum(ShipmentItem.shipped_qty)).filter(
                    ShipmentItem.po_item_id == po_item.id
                ).scalar() or 0

                remaining_qty = po_item.quantity - already_shipped

                if item_in.shipped_qty > remaining_qty:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Overshipment Error: PO Item {po_item.id} only has {remaining_qty} units remaining."
                    )

                # 5. Create Shipment Line
                db_shipment_item = ShipmentItem(
                    shipment_header_id=db_shipment.id,
                    po_item_id=item_in.po_item_id,
                    shipped_qty=item_in.shipped_qty,
                    package_id=item_in.package_id,
                    gross_weight=item_in.gross_weight
                )
                db.add(db_shipment_item)

                # 6. Commercial Status Update
                # If fully shipped, update PO Item status (Lookup ID 4 = 'SHIPPED')
                if item_in.shipped_qty == remaining_qty:
                    po_item.status_id = 4 # Should use a constant or config

            db.commit()
            db.refresh(db_shipment)
            return db_shipment

        except Exception as e:
            db.rollback()
            raise e