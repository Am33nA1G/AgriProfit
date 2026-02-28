"""Road distance cache model — stores OSRM-computed route distances."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RoadDistanceCache(Base):
    __tablename__ = "road_distance_cache"
    __table_args__ = (
        UniqueConstraint("origin_key", "destination_key", name="uq_road_distance_route"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    origin_key: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_key: Mapped[str] = mapped_column(String(32), nullable=False)
    src_lat: Mapped[float] = mapped_column(Float, nullable=False)
    src_lon: Mapped[float] = mapped_column(Float, nullable=False)
    dst_lat: Mapped[float] = mapped_column(Float, nullable=False)
    dst_lon: Mapped[float] = mapped_column(Float, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'osrm' or 'estimated'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
