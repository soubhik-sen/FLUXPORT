from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.shipment import ShipmentHeader, ShipmentItem
from app.models.purchase_order import PurchaseOrderItem
from app.models.po_schedule_line import POScheduleLine
from app.models.logistics_lookups import ShipTypeLookup, ShipmentStatusLookup, TransportModeLookup
from app.schemas.shipment import ShipmentHeaderCreate
from app.services.number_range_get import NumberRangeService

class LogisticsService:
    @staticmethod
    def _resolve_lookup_id(db: Session, model, code_field: str, preferred_codes: list[str]) -> int:
        if preferred_codes:
            for code in preferred_codes:
                row = db.query(model).filter(
                    getattr(model, code_field) == code,
                    model.is_active == True
                ).first()
                if row:
                    return row.id
        row = db.query(model).filter(model.is_active == True).order_by(model.id.asc()).first()
        if not row:
            raise HTTPException(status_code=400, detail=f"No active {model.__tablename__} configured.")
        return row.id

    @staticmethod
    def _resolve_ship_type_id(db: Session, type_id: int | None) -> int:
        if type_id:
            return type_id
        return LogisticsService._resolve_lookup_id(
            db,
            ShipTypeLookup,
            "type_code",
            ["STD", "STANDARD"]
        )

    @staticmethod
    def _resolve_status_id(db: Session, status_id: int | None) -> int:
        if status_id:
            return status_id
        return LogisticsService._resolve_lookup_id(
            db,
            ShipmentStatusLookup,
            "status_code",
            ["BOOKED", "PLANNED", "DRAFT"]
        )

    @staticmethod
    def _resolve_mode_id(db: Session, mode_id: int | None) -> int:
        if mode_id:
            return mode_id
        return LogisticsService._resolve_lookup_id(
            db,
            TransportModeLookup,
            "mode_code",
            ["SEA", "AIR", "ROAD", "RAIL"]
        )

    @staticmethod
    def create_shipment_with_validation(db: Session, shipment_in: ShipmentHeaderCreate, user_email: str):
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
            type_id = LogisticsService._resolve_ship_type_id(db, getattr(shipment_in, "type_id", None))
            status_id = LogisticsService._resolve_status_id(db, getattr(shipment_in, "status_id", None))
            mode_id = LogisticsService._resolve_mode_id(db, getattr(shipment_in, "mode_id", None))
            shipment_number = shipment_in.shipment_number
            if not shipment_number:
                shipment_number = NumberRangeService.get_next_number(db, "SHIPMENT", type_id)

            db_shipment = ShipmentHeader(
                shipment_number=shipment_number,
                external_reference=getattr(shipment_in, "external_reference", None),
                type_id=type_id,
                status_id=status_id,
                mode_id=mode_id,
                carrier_id=shipment_in.carrier_id,
                pol_port_id=getattr(shipment_in, "pol_port_id", None),
                pod_port_id=getattr(shipment_in, "pod_port_id", None),
                estimated_departure=shipment_in.estimated_departure,
                estimated_arrival=shipment_in.estimated_arrival,
                created_by=user_email,
                last_changed_by=user_email,
            )
            db.add(db_shipment)
            db.flush() # Secure Shipment ID

            requested_item_qty: dict[int, float] = {}
            requested_schedule_qty: dict[int, float] = {}

            for index, item_in in enumerate(shipment_in.items, start=1):
                # 3. Enterprise Guard: Fetch the associated PO Item
                po_item = db.query(PurchaseOrderItem).filter(
                    PurchaseOrderItem.id == item_in.po_item_id
                ).with_for_update().first() # Row-level lock for concurrency safety

                if not po_item:
                    raise HTTPException(status_code=404, detail=f"PO Item {item_in.po_item_id} not found")

                request_qty = float(item_in.shipped_qty)

                schedule_line_id = getattr(item_in, "po_schedule_line_id", None)
                if schedule_line_id:
                    schedule_line = db.query(POScheduleLine).filter(
                        POScheduleLine.id == schedule_line_id
                    ).with_for_update().first()
                    if not schedule_line:
                        raise HTTPException(status_code=404, detail=f"Schedule line {schedule_line_id} not found")
                    if schedule_line.po_item_id != po_item.id:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Schedule line {schedule_line_id} does not belong to PO item {po_item.id}."
                        )
                else:
                    schedule_line = db.query(POScheduleLine).filter(
                        POScheduleLine.po_item_id == po_item.id
                    ).order_by(POScheduleLine.schedule_number.asc()).with_for_update().first()
                    if not schedule_line:
                        raise HTTPException(
                            status_code=404,
                            detail=f"No schedule lines found for PO item {po_item.id}."
                        )
                    schedule_line_id = schedule_line.id

                # 4. Fulfillment Logic: Validation
                # 4a) Item-level remaining (include allocations in this request)
                already_shipped_item = db.query(func.sum(ShipmentItem.shipped_qty)).filter(
                    ShipmentItem.po_item_id == po_item.id
                ).scalar() or 0
                pending_item = requested_item_qty.get(po_item.id, 0.0)
                remaining_item = float(po_item.quantity) - float(already_shipped_item) - pending_item
                if request_qty > remaining_item + 1e-9:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Overshipment Error: PO Item {po_item.id} only has "
                            f"{remaining_item:.3f} units remaining."
                        ),
                    )

                # 4b) Schedule-line remaining (authoritative for grouping/finalize)
                already_shipped_schedule = db.query(func.sum(ShipmentItem.shipped_qty)).filter(
                    ShipmentItem.po_schedule_line_id == schedule_line_id
                ).scalar() or 0
                pending_schedule = requested_schedule_qty.get(schedule_line_id, 0.0)
                remaining_schedule = (
                    float(schedule_line.quantity) - float(already_shipped_schedule) - pending_schedule
                )
                if request_qty > remaining_schedule + 1e-9:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Overshipment Error: Schedule line {schedule_line_id} only has "
                            f"{remaining_schedule:.3f} units remaining."
                        ),
                    )

                existing_header_id = schedule_line.shipment_header_id if schedule_line else None
                if existing_header_id is not None and existing_header_id != db_shipment.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Schedule line {schedule_line_id} is already linked to "
                            f"shipment header {existing_header_id}."
                        ),
                    )

                po_number = None
                if po_item.header is not None:
                    po_number = po_item.header.po_number

                # 5. Create Shipment Line
                db_shipment_item = ShipmentItem(
                    shipment_header_id=db_shipment.id,
                    po_item_id=item_in.po_item_id,
                    po_schedule_line_id=schedule_line_id,
                    po_number=po_number,
                    predecessor_doc=po_number,
                    predecessor_item_no=po_item.item_number if po_item else None,
                    shipment_item_number=index,
                    shipped_qty=request_qty,
                    package_id=item_in.package_id,
                    gross_weight=item_in.gross_weight
                )
                db.add(db_shipment_item)

                # Link schedule line to this shipment header for grouping visibility
                if schedule_line is not None:
                    schedule_line.shipment_header_id = db_shipment.id

                requested_item_qty[po_item.id] = pending_item + request_qty
                requested_schedule_qty[schedule_line_id] = pending_schedule + request_qty

                # 6. Commercial Status Update
                # If fully shipped, update PO Item status (Lookup ID 4 = 'SHIPPED')
                item_remaining_after_line = remaining_item - request_qty
                if item_remaining_after_line <= 1e-9:
                    po_item.status_id = 4 # Should use a constant or config

            db.commit()
            db.refresh(db_shipment)
            return db_shipment

        except Exception as e:
            db.rollback()
            raise e
