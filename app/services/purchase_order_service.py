from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.po_schedule_line import POScheduleLine
from app.models.partner_master import PartnerMaster
from app.schemas.purchase_order import POHeaderCreate
from app.services.number_range_get import NumberRangeService

class PurchaseOrderService:
    @staticmethod
    def create_purchase_order(db: Session, po_in: POHeaderCreate, user_email: str) -> PurchaseOrderHeader:
        """
        Enterprise-Grade PO Creation Logic:
        1. Vendor Validation (Master Data Integrity)
        2. Financial Calculation Validation (Commercial Integrity)
        3. Initial Status Assignment (Workflow Integrity)
        4. Atomic Persistence
        """
        try:
            with db.begin():
                # 1. Master Data Validation
                # Ensure the vendor exists and is active before proceeding
                vendor = db.query(PartnerMaster).filter(
                    PartnerMaster.id == po_in.vendor_id,
                    PartnerMaster.is_active == True
                ).first()
                
                if not vendor:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Vendor with ID {po_in.vendor_id} is invalid or inactive."
                    )
                
                if po_in.forwarder_id is not None:
                    forwarder = db.query(PartnerMaster).filter(
                        PartnerMaster.id == po_in.forwarder_id,
                        PartnerMaster.is_active == True
                    ).first()
                    if not forwarder:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Forwarder with ID {po_in.forwarder_id} is invalid or inactive."
                        )

                # 2. Header Preparation
                header_data = po_in.model_dump(exclude={'items', 'created_by', 'last_changed_by'})
                po_number = (header_data.get("po_number") or "").strip()
                if not po_number:
                    po_number = NumberRangeService.get_next_number(db, "PO", po_in.type_id)
                header_data["po_number"] = po_number
                db_po = PurchaseOrderHeader(
                    **header_data,
                    created_by=user_email,
                    last_changed_by=user_email,
                )
                
                # Use constant-based status assignment from your lookup table
                # Example: 1 might be 'DRAFT' or 'NEW'
                db_po.status_id = 1 
                
                db.add(db_po)
                db.flush()  # Obtain db_po.id for child records

                # 3. Item Processing & Financial Check
                calculated_total = 0
                for item_in in po_in.items:
                    # Server-side re-calculation of line totals (Don't trust the client)
                    line_amount = item_in.quantity * item_in.unit_price
                    calculated_total += line_amount
                    
                    db_item = PurchaseOrderItem(
                        **item_in.model_dump(exclude={'line_total', 'schedules'}),
                        po_header_id=db_po.id,
                        line_total=line_amount
                    )
                    db.add(db_item)
                    db.flush()  # Obtain db_item.id for schedule lines

                    schedules = getattr(item_in, "schedules", None) or []
                    for idx, sched_in in enumerate(schedules, start=1):
                        sched_number = sched_in.schedule_number or idx
                        db_sched = POScheduleLine(
                            po_item_id=db_item.id,
                            schedule_number=sched_number,
                            quantity=sched_in.quantity,
                            delivery_date=sched_in.delivery_date,
                        )
                        db.add(db_sched)

                # 4. Final Header Total Update
                db_po.total_amount = calculated_total

            db.refresh(db_po)
            return db_po

        except IntegrityError as e:
            db.rollback()
            # Enterprise error handling for duplicate PO numbers
            if "unique constraint" in str(e.orig).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Purchase Order {po_in.po_number} already exists."
                )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data integrity violation.")
        except Exception as e:
            db.rollback()
            raise e
        
    @staticmethod
    def get_po_by_id(db: Session, po_id: int):
        """
        Enterprise-Grade Fetch:
        Uses 'joinedload' to fetch Items and Lookup names in a SINGLE SQL query.
        This reduces database round-trips significantly.
        """
        return db.query(PurchaseOrderHeader).options(
            joinedload(PurchaseOrderHeader.items),
            joinedload(PurchaseOrderHeader.status),      # Joins po_status_lookup
            joinedload(PurchaseOrderHeader.po_type),     # Joins po_type_lookup
            joinedload(PurchaseOrderHeader.vendor)       # Joins partner_master
        ).filter(PurchaseOrderHeader.id == po_id).first()

    @staticmethod
    def get_multi_pos(db: Session, skip: int = 0, limit: int = 100, vendor_id: int = None):
        """
        Paginated fetch with optional filtering. 
        In enterprise apps, we never return 'all' records; we always paginate.
        """
        query = db.query(PurchaseOrderHeader).options(
            joinedload(PurchaseOrderHeader.status)
        )
        
        if vendor_id:
            query = query.filter(PurchaseOrderHeader.vendor_id == vendor_id)
            
        return query.order_by(PurchaseOrderHeader.created_at.desc()).offset(skip).limit(limit).all()
