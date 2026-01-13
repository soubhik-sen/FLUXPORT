from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ObjectType(Base):
    __tablename__ = "object_types"

    # PK is a short code like OR / PO / IV
    object_type: Mapped[str] = mapped_column(String(10), primary_key=True)

    object_description: Mapped[str] = mapped_column(String(255), nullable=False)
