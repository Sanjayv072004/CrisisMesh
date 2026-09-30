"""Domain Models for Crisis Reports, Sensors, and Verification Results."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class Report(BaseModel):
    """An individual incoming incident report (untrusted data)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    source_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lat: float
    lon: float
    claimed_type: str = "flood"
    claimed_severity: int = Field(default=3, ge=1, le=5)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SensorReading(BaseModel):
    """Ground-truth telemetry from physical sensors (e.g. water level gauge, rain gauge)."""
    sensor_id: str
    sensor_type: str = "water_level"
    lat: float
    lon: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    value: float
    unit: str = "meters"
    flood_threshold: float = 0.5
    coverage_radius_m: float = 1000.0


class ReportCluster(BaseModel):
    """Group of near-identical reports representing ONE corroboration set."""
    cluster_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reports: List[Report] = Field(default_factory=list)
    centroid_lat: float = 0.0
    centroid_lon: float = 0.0
    latest_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unique_sources: List[str] = Field(default_factory=list)

    def update_metadata(self) -> None:
        """Recompute centroid coordinates and unique sources from internal reports."""
        if not self.reports:
            return
        self.centroid_lat = sum(r.lat for r in self.reports) / len(self.reports)
        self.centroid_lon = sum(r.lon for r in self.reports) / len(self.reports)
        self.latest_timestamp = max(r.timestamp for r in self.reports)
        self.unique_sources = sorted(list({r.source_id for r in self.reports}))


class VerificationResult(BaseModel):
    """Deterministic output produced by the Verification Engine."""
    cluster_id: str
    credibility_score: float = Field(ge=0.0, le=1.0)
    label: str  # "confirmed", "conflicting", "unverified"
    has_conflict: bool = False
    reasons: List[str] = Field(default_factory=list)
    factors: Dict[str, float] = Field(default_factory=dict)
