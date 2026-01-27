from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime
from app.models import SysNumberRange    # Assuming it's in models.py
from app.schemas.number_range import NumberRangeCreate, NumberRangeUpdate 


class NumberRangeService:
    @staticmethod
    def get_next_number(db: Session, category: str, type_id: int) -> str:
        """
        Atomic Read-Lock-Update to generate the next document number.
        """
        # 1. Row-level lock (SELECT ... FOR UPDATE)
        # This blocks other transactions from reading this specific row until we commit
        stmt = (
            select(SysNumberRange)
            .where(SysNumberRange.doc_category == category)
            .where(SysNumberRange.doc_type_id == type_id)
            .where(SysNumberRange.is_active == True)
            .with_for_update() 
        )
        
        result = db.execute(stmt)
        range_config = result.scalar_one_or_none()

        if not range_config:
            raise ValueError(f"No active number range found for {category} with type {type_id}")

        # 2. Increment the counter
        range_config.current_value += 1
        
        # 3. Assemble the formatted string
        # Handle Padding (e.g., 105 -> '00105')
        padded_number = str(range_config.current_value).zfill(range_config.padding)
        
        # Handle Year (optional)
        year_str = f"{datetime.now().year}-" if range_config.include_year else ""
        
        formatted_id = f"{range_config.prefix}{year_str}{padded_number}"

        # 4. Return the string (The actual DB Update happens when db.commit() is called by the caller)
        return formatted_id
    
    @staticmethod
    def list_ranges(db: Session):
        return db.query(SysNumberRange).all()

    @staticmethod
    def create_range(db: Session, schema: NumberRangeCreate):
        # Check if sequence already exists for this category/type combo
        existing = db.query(SysNumberRange).filter(
            SysNumberRange.doc_category == schema.doc_category,
            SysNumberRange.doc_type_id == schema.doc_type_id
        ).first()
        
        if existing:
            raise ValueError("A sequence already exists for this category and type.")
            
        new_range = SysNumberRange(**schema.dict())
        db.add(new_range)
        db.commit()
        db.refresh(new_range)
        return new_range

    @staticmethod
    def update_range(db: Session, range_id: int, schema: NumberRangeUpdate):
        db_range = db.query(SysNumberRange).filter(SysNumberRange.id == range_id).first()
        if not db_range:
            return None
            
        for key, value in schema.dict(exclude_unset=True).items():
            setattr(db_range, key, value)
            
        db.commit()
        db.refresh(db_range)
        return db_range

    @staticmethod
    def delete_range(db: Session, range_id: int) -> bool:
        db_range = db.query(SysNumberRange).filter(SysNumberRange.id == range_id).first()
        if not db_range:
            return False

        db.delete(db_range)
        db.commit()
        return True
