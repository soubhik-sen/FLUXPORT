from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    id: Any
    __name__: str

    # Enterprise Convention: 
    # Class 'PurchaseOrder' automatically becomes table 'purchase_order'
    @declared_attr
    def __tablename__(cls) -> str:
        import re
        # Converts CamelCase to snake_case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()