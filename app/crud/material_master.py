from app.crud.base_lookup import CRUDBase
from app.models.product_master import (
    MaterialCustomerMap,
    MaterialPlantData,
    MaterialSupplierMap,
    MaterialText,
    MaterialUomConversion,
    ProductMaster,
)


crud_material_master = CRUDBase(ProductMaster)
crud_material_text = CRUDBase(MaterialText)
crud_material_plant_data = CRUDBase(MaterialPlantData)
crud_material_uom_conversion = CRUDBase(MaterialUomConversion)
crud_material_supplier_map = CRUDBase(MaterialSupplierMap)
crud_material_customer_map = CRUDBase(MaterialCustomerMap)
