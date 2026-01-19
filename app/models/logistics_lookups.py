from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ShipmentStatusLookup(Base):
    """Lookup for shipment lifecycle (e.g., BOOKED, IN_TRANSIT, DELIVERED)."""
    __tablename__ = "shipment_status_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

class TransportModeLookup(Base):
    """Lookup for transport modes (e.g., SEA, AIR, ROAD, RAIL)."""
    __tablename__ = "transport_mode_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mode_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    mode_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# ... (existing ShipmentStatusLookup and TransportModeLookup)

class MilestoneTypeLookup(Base):
    """
    Lookup for specific logistics events.
    Examples: 'DEPARTED', 'ARRIVED_PORT', 'CUSTOMS_CLEARED', 'GATED_IN'.
    """
    __tablename__ = "milestone_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    milestone_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    milestone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ContainerTypeLookup(Base):
    """
    Lookup for container sizes/types.
    Examples: '20GP' (20ft General), '40HC' (40ft High Cube), 'REF' (Reefer).
    """
    __tablename__ = "container_type_lookup"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    container_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    container_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)