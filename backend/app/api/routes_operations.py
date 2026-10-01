"""Operational API Routes: Ingestion of Reports, Sensors, Unit Status & Road Blockages."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.schemas import (
    ReportIngestRequest, ReportIngestResponse, SensorIngestRequest, UnitStatusUpdateRequest, RoadBlockRequest
)
from backend.app.api.auth import require_permission, get_current_user
from backend.app.security.rbac import Permission, UserToken
from backend.app.api.state_manager import state_manager

router = APIRouter(tags=["Operations & Ingestion"])


@router.post("/reports", response_model=ReportIngestResponse)
def submit_report(
    req: ReportIngestRequest,
    user: UserToken = Depends(require_permission(Permission.SUBMIT_REPORT)),
):
    """Submit raw citizen or agency report. Requires OPERATOR or COMMANDER role."""
    result = state_manager.ingest_report(
        text=req.text,
        source_id=req.source_id,
        lat=req.lat,
        lon=req.lon,
        ip_address=req.ip_address,
    )

    if result.get("status") == "AUTH_REJECTED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Spoofed source authentication rejected.")
    if result.get("status") == "RATE_LIMITED":
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")

    return ReportIngestResponse(
        report_id=result.get("report_id"),
        status=result.get("status", "INGESTED"),
        is_quarantined=result.get("is_quarantined", False),
        confidence=result.get("confidence", 0.5),
        security_events=result.get("security_events", []),
    )


@router.post("/sensors")
def submit_sensor_reading(req: SensorIngestRequest):
    """Ingest physical telemetry (water gauges, rain meters). Requires valid HMAC-SHA256 signature."""
    result = state_manager.ingest_sensor(
        sensor_id=req.sensor_id,
        sensor_type=req.sensor_type,
        lat=req.lat,
        lon=req.lon,
        value=req.value,
        unit=req.unit,
        signature_hex=req.signature_hex,
        flood_threshold=req.flood_threshold,
    )

    if result.get("status") == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Cryptographic verification rejected: {result.get('reason')}",
        )

    return result


@router.post("/units/{unit_id}/status")
def update_unit_status(
    unit_id: str,
    req: UnitStatusUpdateRequest,
    user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN)),
):
    """Update emergency unit operational state (idle, en_route, unavailable). Triggers selective re-plan."""
    result = state_manager.update_unit_status(
        unit_id=unit_id,
        new_status=req.status,
        target_id=req.current_target_id,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.post("/roads/block")
def block_road(
    req: RoadBlockRequest,
    user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN)),
):
    """Dynamically declare a road segment (u, v) or geographical zone blocked by floods."""
    result = state_manager.block_road(
        u=req.u,
        v=req.v,
        lat=req.lat,
        lon=req.lon,
        radius_km=req.radius_km,
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.get("/map/graph")
def get_map_graph():
    """Return the road network graph with node coordinates and edge blockage statuses."""
    engine = state_manager.orchestrator.impact.engine
    nodes = []
    for node_id, data in engine.graph.nodes(data=True):
        nodes.append({
            "id": node_id,
            "name": data.get("name", node_id),
            "lat": float(data.get("lat", 0.0)),
            "lon": float(data.get("lon", 0.0)),
        })
    edges = []
    for u, v, data in engine.graph.edges(data=True):
        edges.append({
            "u": u,
            "v": v,
            "is_blocked": bool(data.get("is_blocked", False)),
            "flood_depth_m": float(data.get("flood_depth_m", 0.0)),
            "travel_time_mins": float(data.get("travel_time_mins", 5.0)),
            "coordinates": [
                [float(engine.graph.nodes[u]["lon"]), float(engine.graph.nodes[u]["lat"])],
                [float(engine.graph.nodes[v]["lon"]), float(engine.graph.nodes[v]["lat"])],
            ]
        })
    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "blocked_count": sum(1 for e in edges if e["is_blocked"]),
        "graph_source": "Cached OpenStreetMap Subgraph (South-East Bengaluru)",
    }
