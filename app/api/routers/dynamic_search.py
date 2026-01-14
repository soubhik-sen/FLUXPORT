# app/api/routers/dynamic_search.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
#from app.api import deps
from app.crud import dynamic
from app.db.session import get_db

router = APIRouter()

@router.get("/metadata/{table_name}")
def read_metadata(table_name: str, db: Session = Depends(get_db)):
    fields = dynamic.get_table_metadata(db, table_name)
    if fields is None:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"fields": fields}

@router.post("/search/{table_name}")
def search_data(table_name: str, filters: dict, db: Session = Depends(get_db)):
    return dynamic.search_dynamic_table(db, table_name, filters)