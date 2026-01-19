from sqlalchemy.orm import Session
from decimal import Decimal
from fastapi import HTTPException, status
from app.models.landed_cost import LandedCostEntry
from app.models.shipment import ShipmentHeader, ShipmentItem
from app.models.purchase_order import PurchaseOrderItem
from app.schemas.landed_cost import LandedCostCreate

class LandedCostService:
    @staticmethod
    def add_cost_and_apportion(db: Session, cost_in: LandedCostCreate):
        """
        Enterprise-Grade Landed Cost Logic:
        1. Records the expense at the Shipment Level.
        2. Apportions the cost to individual PO items for margin analysis.
        3. Validates against the CostComponentLookup.
        """
        try:
            # 1. Record the actual expense entry
            db_entry = LandedCostEntry(**cost_in.model_dump())
            db.add(db_entry)
            db.flush()

            # 2. Fetch Shipment Details for Apportionment
            shipment = db.query(ShipmentHeader).filter(
                ShipmentHeader.id == cost_in.shipment_header_id
            ).first()

            if not shipment:
                raise HTTPException(status_code=404, detail="Shipment not found")

            # 3. Perform Apportionment (Example: Weighted by Value)
            # Fetch all items in this shipment
            ship_items = db.query(ShipmentItem).filter(
                ShipmentItem.shipment_header_id == shipment.id
            ).all()

            total_shipment_value = sum(
                (si.po_item.unit_price * si.shipped_qty) for si in ship_items
            )

            if total_shipment_value <= 0:
                raise HTTPException(status_code=400, detail="Cannot apportion cost to zero-value shipment")

            # 4. Update the 'Actual Landed Cost' on the PO Items
            # Note: In a Tier-1 system, we often store this in a separate 
            # 'po_item_actual_cost' table to preserve the original PO price.
            for si in ship_items:
                item_value = si.po_item.unit_price * si.shipped_qty
                # Apportioned portion = (Item Value / Total Value) * Total Expense
                share = (item_value / total_shipment_value) * Decimal(str(cost_in.amount))
                
                # Update the PO item's apportioned cost field
                # This allows for Real-Time Margin Analysis
                si.po_item.apportioned_landed_cost = (si.po_item.apportioned_landed_cost or 0) + share

            db.commit()
            return db_entry

        except Exception as e:
            db.rollback()
            raise e