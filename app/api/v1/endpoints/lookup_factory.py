from typing import Type, List, Any
from fastapi import APIRouter, Depends, status, Body, HTTPException  # Import Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.crud.base_lookup import CRUDBase
from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

def create_lookup_router(
    model: Any,
    schema: Type[BaseModel], 
    name: str,
    tags: List[str]
) -> APIRouter:
    router = APIRouter(tags=tags) # Added tags here so they show in Swagger
    crud = CRUDBase(model)
    # Helper to get actual DB column names dynamically
    def get_column_names():
        mapper = inspect(model)
        return [c.key for c in mapper.attrs]
    
    @router.get("")
    @router.get("/")
    def read_lookups(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
        db_items = crud.get_multi(db, skip=skip, limit=limit)
        return jsonable_encoder(db_items)

    @router.post("", status_code=status.HTTP_201_CREATED)
    @router.post("/", status_code=status.HTTP_201_CREATED)
    def create_lookup(
        db: Session = Depends(get_db),
        obj_in: Any = Body(...) 
    ):
        # --- STEP 1: NORMALIZE (For Pydantic) ---
        # Map 'transp_code' -> 'code' so schema.model_validate works
        normalized_input = {}
        for key, value in obj_in.items():
            if key.endswith('_code'):
                normalized_input['code'] = value
            elif key.endswith('_name'):
                normalized_input['name'] = value
            else:
                normalized_input[key] = value

        # --- STEP 2: VALIDATE ---
        validated_data = schema.model_validate(normalized_input)
        generic_dict = validated_data.model_dump(exclude_unset=True)

        # --- STEP 3: DENORMALIZE (For SQLAlchemy) ---
        # Detect the actual model column names (e.g., mode_code)
        db_ready_data = {}
        
        # We look at the Model's columns to see what they are actually named
        mapper = inspect(model)
        column_names = [c.key for c in mapper.attrs]

        for key, value in generic_dict.items():
            if key == 'code':
                # Find the column that ends in _code (e.g., mode_code)
                actual_key = next((c for c in column_names if c.endswith('_code')), 'code')
                db_ready_data[actual_key] = value
            elif key == 'name':
                # Find the column that ends in _name (e.g., mode_name)
                actual_key = next((c for c in column_names if c.endswith('_name')), 'name')
                db_ready_data[actual_key] = value
            else:
                db_ready_data[key] = value

        # --- STEP 4: CREATE ---
        # Bypass generic CRUD and use the model directly with correct keys
        db_obj = model(**db_ready_data)
        db.add(db_obj)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc.orig))
        db.refresh(db_obj)
        return (db_obj)
    
    @router.put("/{id}")
    def update_lookup(id: int, db: Session = Depends(get_db), obj_in: Any = Body(...)):
            db_obj = db.query(model).filter(model.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"{name} not found")

            # Reuse Denormalization Logic for the Update
            column_names = get_column_names()
            for key, value in obj_in.items():
                # If incoming key is generic 'code', map to 'mode_code'
                if key == 'code' or key.endswith('_code'):
                    actual_key = next((c for c in column_names if c.endswith('_code')), key)
                    setattr(db_obj, actual_key, value)
                elif key == 'name' or key.endswith('_name'):
                    actual_key = next((c for c in column_names if c.endswith('_name')), key)
                    setattr(db_obj, actual_key, value)
                else:
                    setattr(db_obj, key, value)

            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(exc.orig))
            db.refresh(db_obj)
            return jsonable_encoder(db_obj)

    @router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_lookup(id: int, db: Session = Depends(get_db)):
            db_obj = db.query(model).filter(model.id == id).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail=f"{name} not found")
            db.delete(db_obj)
            db.commit()
            return None
        


    return router
