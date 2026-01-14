# app/crud/dynamic.py
from sqlalchemy import inspect, Table, MetaData, cast, String, or_
from sqlalchemy.orm import Session

def get_table_metadata(db: Session, table_name: str):
    inspector = inspect(db.get_bind())
    if table_name not in inspector.get_table_names():
        return None
    
    pk_columns = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
    index_columns = []
    for index in inspector.get_indexes(table_name):
        index_columns.extend(index["column_names"])
        
    return list(set(pk_columns + index_columns))

def search_dynamic_table(db: Session, table_name: str, filters: dict):
    metadata = MetaData()
    # Reflecting the table structure
    target_table = Table(table_name, metadata, autoload_with=db.get_bind())
    query = target_table.select()
    
    conditions = []
    for col, val in filters.items():
        if val and col in target_table.c:
            conditions.append(cast(target_table.c[col], String).ilike(val))
            
    if conditions:
        query = query.where(or_(*conditions))
    
    result = db.execute(query)
    return [dict(row._mapping) for row in result]