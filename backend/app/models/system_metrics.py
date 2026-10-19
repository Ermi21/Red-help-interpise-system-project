"""
Time-series system metrics written by the background collector every 15 s.
Used by the Server Monitoring dashboard for live charts.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # CPU
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Memory
    mem_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    mem_used_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    mem_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Disk (root)
    disk_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_used_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Network (cumulative bytes — delta computed in the API layer)
    net_bytes_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_bytes_recv: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Request metrics (counters reset each interval)
    requests_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requests_error: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_sysmetric_collected_at", "collected_at"),
    )
