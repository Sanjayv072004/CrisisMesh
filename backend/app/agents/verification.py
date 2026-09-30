"""Verification Agent: Deterministic Truth Assessment & Sensor Corroboration."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import IncidentRecord, SensorReading, VerificationLabel
from backend.app.engines.verification import cluster_duplicates, credibility_score, label


class VerificationAgent(BaseAgent):
    """Evaluates report credibility, clusters duplicate spam, and corroborates physical sensors."""

    def __init__(
        self,
        bus: MessageBus,
        source_registry: Optional[Dict[str, float]] = None,
        sensors: Optional[List[Any]] = None,
        raw_reports: Optional[Dict[str, Any]] = None,
    ):
        manifest = PermissionManifest(
            allowed_tools={"credibility_scorer", "duplicate_clusterer", "labeler"},
            allowed_inbound={"IncidentParsed", "ClarificationResponse", "SensorAlert"},
            allowed_outbound={"IncidentVerified", "ClarificationRequest"}
        )
        tools = {
            "credibility_scorer": credibility_score,
            "duplicate_clusterer": cluster_duplicates,
            "labeler": label,
        }
        super().__init__(name="Verification", role="Truth & Credibility Assessor", manifest=manifest, bus=bus, tools=tools)

        # Lazy load from scenario.json if any are omitted
        if source_registry is None or sensors is None or raw_reports is None:
            try:
                import json
                from pathlib import Path
                sc_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "scenario.json"
                if sc_path.exists():
                    with open(sc_path, "r", encoding="utf-8-sig") as f:
                        sc_data = json.load(f)
                    if source_registry is None:
                        source_registry = sc_data.get("source_registry", {})
                    if sensors is None:
                        sensors = sc_data.get("sensors", [])
                    if raw_reports is None:
                        raw_reports = {r["id"]: r for r in sc_data.get("raw_reports", [])}
            except Exception:
                pass

        self.source_registry = source_registry or {
            "traffic_police_hq": 0.95,
            "bbmp_control_room": 0.92,
            "sdrf_operator": 0.90,
            "verified_volunteer_01": 0.82,
            "citizen_sanjay": 0.55,
            "unverified_anonymous": 0.25,
            "anonymous_burner_99": 0.10,
            "botnet_cluster_alpha": 0.05
        }
        self.sensors = sensors or []
        self.raw_reports: Dict[str, Any] = raw_reports or {}
        self._clarification_sent: set[str] = set()

    def process_incident(
        self,
        incident: IncidentRecord,
        raw_reports_map: Optional[Dict[str, Any]] = None,
        trace_id: str = "trace-verify"
    ) -> IncidentRecord:
        """Process an incident: query clarification if ambiguous, otherwise compute label."""
        if raw_reports_map:
            self.raw_reports.update(raw_reports_map)

        # 1. Ambiguity / missing fields check
        if incident.ambiguous_fields and incident.id not in self._clarification_sent:
            self._clarification_sent.add(incident.id)
            self.send_message(
                receiver="Situation",
                message_type="ClarificationRequest",
                payload={"incident_id": incident.id, "ambiguous_fields": incident.ambiguous_fields},
                trace_id=trace_id
            )
            return incident

        # 2. Gather linked raw reports
        from backend.app.models.incident import Report as EngReport, SensorReading as EngSensor
        eng_reports = []
        if incident.report_ids:
            for rid in incident.report_ids:
                raw_rep = self.raw_reports.get(rid)
                if raw_rep:
                    if isinstance(raw_rep, dict):
                        ts = raw_rep.get("timestamp")
                        if isinstance(ts, str):
                            try:
                                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            except Exception:
                                ts = datetime.now(timezone.utc)
                        elif not isinstance(ts, datetime):
                            ts = datetime.now(timezone.utc)
                        eng_reports.append(EngReport(
                            id=raw_rep.get("id", rid),
                            text=raw_rep.get("text", incident.description or incident.title),
                            source_id=raw_rep.get("source_id", "unverified_anonymous"),
                            timestamp=ts,
                            lat=raw_rep.get("lat", incident.lat),
                            lon=raw_rep.get("lon", incident.lon),
                            claimed_type=str(raw_rep.get("claimed_type", incident.required_unit_type.value if hasattr(incident.required_unit_type, "value") else incident.required_unit_type)),
                            claimed_severity=raw_rep.get("claimed_severity", incident.severity)
                        ))
                    elif hasattr(raw_rep, "text"):
                        eng_reports.append(EngReport(
                            id=getattr(raw_rep, "id", rid),
                            text=raw_rep.text,
                            source_id=getattr(raw_rep, "source_id", "unverified_anonymous"),
                            timestamp=getattr(raw_rep, "timestamp", datetime.now(timezone.utc)),
                            lat=raw_rep.lat,
                            lon=raw_rep.lon,
                            claimed_type=str(getattr(raw_rep, "claimed_type", incident.required_unit_type.value if hasattr(incident.required_unit_type, "value") else incident.required_unit_type)),
                            claimed_severity=getattr(raw_rep, "claimed_severity", incident.severity)
                        ))

        # Fallback if no linked report found: use incident data with anonymous prior
        if not eng_reports:
            eng_reports.append(EngReport(
                id=incident.id,
                text=incident.description or incident.title,
                source_id=getattr(incident, "source_id", None) or "unverified_anonymous",
                timestamp=incident.reported_at,
                lat=incident.lat,
                lon=incident.lon,
                claimed_type=str(incident.required_unit_type.value if hasattr(incident.required_unit_type, "value") else incident.required_unit_type),
                claimed_severity=incident.severity
            ))

        # Prepare sensors with per-sensor coverage_radius_m
        eng_sensors = []
        for s in self.sensors:
            if isinstance(s, dict):
                s_ts = s.get("timestamp")
                if isinstance(s_ts, str):
                    try:
                        s_ts = datetime.fromisoformat(s_ts.replace("Z", "+00:00"))
                    except Exception:
                        s_ts = datetime.now(timezone.utc)
                elif not isinstance(s_ts, datetime):
                    s_ts = datetime.now(timezone.utc)
                eng_sensors.append(EngSensor(
                    sensor_id=s["sensor_id"],
                    sensor_type=s.get("sensor_type", "water_level"),
                    lat=s["lat"],
                    lon=s["lon"],
                    timestamp=s_ts,
                    value=s["value"],
                    unit=s.get("unit", "meters"),
                    flood_threshold=s.get("flood_threshold", 0.5),
                    coverage_radius_m=s.get("coverage_radius_m", 1000.0)
                ))
            else:
                eng_sensors.append(EngSensor(
                    sensor_id=s.sensor_id,
                    sensor_type=s.sensor_type,
                    lat=s.lat,
                    lon=s.lon,
                    timestamp=s.timestamp,
                    value=s.value,
                    unit=s.unit,
                    flood_threshold=s.flood_threshold,
                    coverage_radius_m=getattr(s, "coverage_radius_m", 1000.0)
                ))

        # Determine evaluation timestamp (accounting for scenario simulation time vs real time)
        latest_rep_time = max([r.timestamp for r in eng_reports], default=datetime.now(timezone.utc))
        if abs((datetime.now(timezone.utc) - latest_rep_time).total_seconds()) > 3600:
            eval_now = latest_rep_time + timedelta(minutes=5)
        else:
            eval_now = datetime.now(timezone.utc)

        score = self.call_tool(
            "credibility_scorer",
            trace_id=trace_id,
            report_cluster=eng_reports,
            sensors=eng_sensors,
            source_registry=self.source_registry,
            now=eval_now
        )

        res_label = self.call_tool("labeler", trace_id=trace_id, score=score, has_conflict=False)

        updated_inc = incident.model_copy(update={
            "credibility_score": score,
            "verification_label": VerificationLabel(res_label)
        })

        self.send_message(
            receiver="Impact",
            message_type="IncidentVerified",
            payload={
                "incident_id": updated_inc.id,
                "credibility_score": score,
                "label": res_label
            },
            trace_id=trace_id
        )
        return updated_inc

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify all active incidents in state."""
        # Update raw reports if provided in state
        raw_reports = state.get("raw_reports", {})
        if isinstance(raw_reports, list):
            raw_reports = {r["id"] if isinstance(r, dict) else r.id: r for r in raw_reports}
        if raw_reports:
            self.raw_reports.update(raw_reports)

        if state.get("sensors"):
            self.sensors = state["sensors"]
        if state.get("source_registry"):
            self.source_registry = state["source_registry"]

        incidents_dict = dict(state.get("incidents", {}))
        labels_dict = dict(state.get("verification_labels", {}))

        for inc_id, inc_data in incidents_dict.items():
            inc = IncidentRecord(**inc_data) if isinstance(inc_data, dict) else inc_data
            verified_inc = self.process_incident(inc, raw_reports_map=self.raw_reports)
            incidents_dict[inc_id] = verified_inc.model_dump()
            labels_dict[inc_id] = verified_inc.verification_label.value

        state["incidents"] = incidents_dict
        state["verification_labels"] = labels_dict
        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
