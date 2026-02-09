from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.material_master import (
    crud_material_customer_map,
    crud_material_master,
    crud_material_plant_data,
    crud_material_supplier_map,
    crud_material_text,
    crud_material_uom_conversion,
)
from app.db.session import get_db
from app.schemas.material_master import (
    MaterialCustomerMapCreate,
    MaterialCustomerMapOut,
    MaterialCustomerMapUpdate,
    MaterialMasterCreate,
    MaterialMasterOut,
    MaterialMasterUpdate,
    MaterialPlantDataCreate,
    MaterialPlantDataOut,
    MaterialPlantDataUpdate,
    MaterialSupplierMapCreate,
    MaterialSupplierMapOut,
    MaterialSupplierMapUpdate,
    MaterialTextCreate,
    MaterialTextOut,
    MaterialTextUpdate,
    MaterialUomConversionCreate,
    MaterialUomConversionOut,
    MaterialUomConversionUpdate,
)

router = APIRouter(tags=["material-maintenance"])


def _integrity_conflict(exc: IntegrityError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc.orig))


def _get_or_404(db: Session, crud_obj, row_id: int, entity_name: str):
    db_obj = crud_obj.get(db, row_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
    return db_obj


def _delete_row(db: Session, crud_obj, row_id: int, entity_name: str):
    db_obj = _get_or_404(db, crud_obj, row_id, entity_name)
    try:
        db.delete(db_obj)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity_conflict(exc)


@router.get("/material_master", response_model=list[MaterialMasterOut])
def list_material_master(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_master.get_multi(db, skip=skip, limit=limit)


@router.get("/material_master/{row_id}", response_model=MaterialMasterOut)
def get_material_master(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_master, row_id, "Material master")


@router.post("/material_master", response_model=MaterialMasterOut, status_code=status.HTTP_201_CREATED)
def create_material_master(payload: MaterialMasterCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_master.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_master/{row_id}", response_model=MaterialMasterOut)
def update_material_master(row_id: int, payload: MaterialMasterUpdate, db: Session = Depends(get_db)):
    db_obj = _get_or_404(db, crud_material_master, row_id, "Material master")
    try:
        return crud_material_master.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_master/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_master(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_master, row_id, "Material master")
    return None


@router.get("/material_text", response_model=list[MaterialTextOut])
def list_material_text(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_text.get_multi(db, skip=skip, limit=limit)


@router.get("/material_text/{row_id}", response_model=MaterialTextOut)
def get_material_text(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_text, row_id, "Material text")


@router.post("/material_text", response_model=MaterialTextOut, status_code=status.HTTP_201_CREATED)
def create_material_text(payload: MaterialTextCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_text.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_text/{row_id}", response_model=MaterialTextOut)
def update_material_text(row_id: int, payload: MaterialTextUpdate, db: Session = Depends(get_db)):
    db_obj = _get_or_404(db, crud_material_text, row_id, "Material text")
    try:
        return crud_material_text.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_text/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_text(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_text, row_id, "Material text")
    return None


@router.get("/material_plant_data", response_model=list[MaterialPlantDataOut])
def list_material_plant_data(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_plant_data.get_multi(db, skip=skip, limit=limit)


@router.get("/material_plant_data/{row_id}", response_model=MaterialPlantDataOut)
def get_material_plant_data(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_plant_data, row_id, "Material plant data")


@router.post("/material_plant_data", response_model=MaterialPlantDataOut, status_code=status.HTTP_201_CREATED)
def create_material_plant_data(payload: MaterialPlantDataCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_plant_data.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_plant_data/{row_id}", response_model=MaterialPlantDataOut)
def update_material_plant_data(row_id: int, payload: MaterialPlantDataUpdate, db: Session = Depends(get_db)):
    db_obj = _get_or_404(db, crud_material_plant_data, row_id, "Material plant data")
    try:
        return crud_material_plant_data.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_plant_data/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_plant_data(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_plant_data, row_id, "Material plant data")
    return None


@router.get("/material_uom_conversion", response_model=list[MaterialUomConversionOut])
def list_material_uom_conversion(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_uom_conversion.get_multi(db, skip=skip, limit=limit)


@router.get("/material_uom_conversion/{row_id}", response_model=MaterialUomConversionOut)
def get_material_uom_conversion(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_uom_conversion, row_id, "Material UOM conversion")


@router.post("/material_uom_conversion", response_model=MaterialUomConversionOut, status_code=status.HTTP_201_CREATED)
def create_material_uom_conversion(payload: MaterialUomConversionCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_uom_conversion.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_uom_conversion/{row_id}", response_model=MaterialUomConversionOut)
def update_material_uom_conversion(
    row_id: int,
    payload: MaterialUomConversionUpdate,
    db: Session = Depends(get_db),
):
    db_obj = _get_or_404(db, crud_material_uom_conversion, row_id, "Material UOM conversion")
    try:
        return crud_material_uom_conversion.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_uom_conversion/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_uom_conversion(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_uom_conversion, row_id, "Material UOM conversion")
    return None


@router.get("/material_supplier_map", response_model=list[MaterialSupplierMapOut])
def list_material_supplier_map(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_supplier_map.get_multi(db, skip=skip, limit=limit)


@router.get("/material_supplier_map/{row_id}", response_model=MaterialSupplierMapOut)
def get_material_supplier_map(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_supplier_map, row_id, "Material supplier map")


@router.post("/material_supplier_map", response_model=MaterialSupplierMapOut, status_code=status.HTTP_201_CREATED)
def create_material_supplier_map(payload: MaterialSupplierMapCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_supplier_map.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_supplier_map/{row_id}", response_model=MaterialSupplierMapOut)
def update_material_supplier_map(
    row_id: int,
    payload: MaterialSupplierMapUpdate,
    db: Session = Depends(get_db),
):
    db_obj = _get_or_404(db, crud_material_supplier_map, row_id, "Material supplier map")
    try:
        return crud_material_supplier_map.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_supplier_map/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_supplier_map(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_supplier_map, row_id, "Material supplier map")
    return None


@router.get("/material_customer_map", response_model=list[MaterialCustomerMapOut])
def list_material_customer_map(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return crud_material_customer_map.get_multi(db, skip=skip, limit=limit)


@router.get("/material_customer_map/{row_id}", response_model=MaterialCustomerMapOut)
def get_material_customer_map(row_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, crud_material_customer_map, row_id, "Material customer map")


@router.post("/material_customer_map", response_model=MaterialCustomerMapOut, status_code=status.HTTP_201_CREATED)
def create_material_customer_map(payload: MaterialCustomerMapCreate, db: Session = Depends(get_db)):
    try:
        return crud_material_customer_map.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.put("/material_customer_map/{row_id}", response_model=MaterialCustomerMapOut)
def update_material_customer_map(
    row_id: int,
    payload: MaterialCustomerMapUpdate,
    db: Session = Depends(get_db),
):
    db_obj = _get_or_404(db, crud_material_customer_map, row_id, "Material customer map")
    try:
        return crud_material_customer_map.update(db, db_obj=db_obj, obj_in=payload)
    except IntegrityError as exc:
        raise _integrity_conflict(exc)


@router.delete("/material_customer_map/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_customer_map(
    row_id: int,
    mode: str = Query("hard", pattern="^(soft|hard)$"),
    db: Session = Depends(get_db),
):
    _delete_row(db, crud_material_customer_map, row_id, "Material customer map")
    return None
