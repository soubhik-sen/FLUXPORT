from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
from app.models.purchase_order import PurchaseOrderHeader, PurchaseOrderItem
from app.models.po_schedule_line import POScheduleLine
from app.models.partner_master import PartnerMaster
from app.models.customer_master import CustomerMaster
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
            tx_ctx = db.begin_nested() if db.in_transaction() else db.begin()
            with tx_ctx:
                # 1. Master Data Validation
                # Ensure the vendor exists and is active before proceeding
                customer = (
                    db.query(CustomerMaster)
                    .filter(
                        CustomerMaster.id == po_in.customer_id,
                        CustomerMaster.is_active == True,
                    )
                    .first()
                )
                if not customer:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Customer with ID {po_in.customer_id} is invalid or inactive.",
                    )
                if customer.company_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Selected customer has no main-branch company mapping. "
                            "Set customer_master.company_id before creating PO."
                        ),
                    )

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
                header_data = po_in.model_dump(
                    exclude={
                        'items',
                        'created_by',
                        'last_changed_by',
                        'texts',
                        'text_profile_id',
                        'text_profile_version',
                        'company_id',
                    }
                )
                # Canonical source: company is always derived from customer mapping.
                header_data["company_id"] = int(customer.company_id)
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
                    if not schedules:
                        # Save-time default: one item -> one schedule line when UI sends no schedules.
                        schedules = [
                            {
                                "schedule_number": 1,
                                "quantity": item_in.quantity,
                                "delivery_date": po_in.order_date,
                            }
                        ]

                    for idx, sched_in in enumerate(schedules, start=1):
                        sched_number = (
                            sched_in.get("schedule_number")
                            if isinstance(sched_in, dict)
                            else sched_in.schedule_number
                        ) or idx
                        quantity = (
                            sched_in.get("quantity")
                            if isinstance(sched_in, dict)
                            else sched_in.quantity
                        )
                        delivery_date = (
                            sched_in.get("delivery_date")
                            if isinstance(sched_in, dict)
                            else sched_in.delivery_date
                        )
                        db_sched = POScheduleLine(
                            po_item_id=db_item.id,
                            schedule_number=sched_number,
                            quantity=quantity,
                            delivery_date=delivery_date,
                        )
                        db.add(db_sched)

                # 4. Final Header Total Update
                db_po.total_amount = calculated_total

            db.refresh(db_po)
            return db_po

        except IntegrityError as e:
            db.rollback()
            detail = str(e.orig)
            if "po_header_company_id_fkey" in detail or (
                "company_id" in detail and "company_master" in detail
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid buyer/company mapping: "
                        "derived company_id does not exist in company_master."
                    ),
                )
            if "po_header_customer_id_fkey" in detail or (
                "customer_id" in detail and "customer_master" in detail
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid customer mapping: customer_id does not exist in customer_master.",
                )
            # Enterprise error handling for duplicate PO numbers
            if "unique constraint" in detail.lower():
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
            joinedload(PurchaseOrderHeader.doc_type),    # Joins po_type_lookup
            joinedload(PurchaseOrderHeader.purchase_org)
        ).filter(PurchaseOrderHeader.id == po_id).first()

    @staticmethod
    def get_multi_pos(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        vendor_id: int = None,
        scope_by_field: dict[str, set[int]] | None = None,
        legacy_customer_company_ids: set[int] | None = None,
    ):
        """
        Paginated fetch with optional filtering. 
        In enterprise apps, we never return 'all' records; we always paginate.
        """
        query = db.query(PurchaseOrderHeader).options(
            joinedload(PurchaseOrderHeader.status)
        )
        
        if vendor_id:
            query = query.filter(PurchaseOrderHeader.vendor_id == vendor_id)

        if scope_by_field:
            clauses = []
            for field_name, ids in scope_by_field.items():
                if not ids:
                    continue
                if field_name == "customer_id":
                    clauses.append(PurchaseOrderHeader.customer_id.in_(sorted(ids)))
                    if legacy_customer_company_ids:
                        clauses.append(
                            and_(
                                PurchaseOrderHeader.customer_id.is_(None),
                                PurchaseOrderHeader.company_id.in_(
                                    sorted(legacy_customer_company_ids)
                                ),
                            )
                        )
                    continue
                column = getattr(PurchaseOrderHeader, field_name, None)
                if column is None:
                    continue
                clauses.append(column.in_(sorted(ids)))
            if clauses:
                query = query.filter(or_(*clauses))
            
        return query.order_by(PurchaseOrderHeader.created_at.desc()).offset(skip).limit(limit).all()
