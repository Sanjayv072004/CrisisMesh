"""Verification Agent: Deterministic Truth Assessment & Sensor Corroboration."""
from __future__ import annotations
from datetime import datetime, timezone
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
        sensors: Optional[List[SensorReading]] = None,
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
        self._clarification_sent: set[str] = set()

    def process_incident(self, incident: IncidentRecord, trace_id: str = "trace-verify") -> IncidentRecord:
        """Process an incident: query clarification if ambiguous, otherwise compute label."""
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

        # 2. Convert incident into single-cluster or evaluate against sensors
        from backend.app.models.incident import Report as EngReport, ReportCluster
        eng_report = EngReport(
            id=incident.id,
            text=incident.description or incident.title,
            source_id="citizen_sanjay",
            timestamp=incident.reported_at,
            lat=incident.lat,
            lon=incident.lon,
            claimed_type=str(incident.required_unit_type),
            claimed_severity=incident.severity
        )
        cluster = ReportCluster(reports=[eng_report])
        cluster.update_metadata()

        from backend.app.models.incident import SensorReading as EngSensor
        eng_sensors = [
            EngSensor(
                sensor_id=s.sensor_id,
                sensor_type=s.sensor_type,
                lat=s.lat,
                lon=s.lon,
                timestamp=s.timestamp,
                value=s.value,
                unit=s.unit,
                flood_threshold=s.flood_threshold
            )
            for s in self.sensors
        ]

        score = self.call_tool(
            "credibility_scorer",
            trace_id=trace_id,
            report_cluster=cluster,
            sensors=eng_sensors,
            source_registry=self.source_registry,
            now=datetime.now(timezone.utc)
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
        incidents_dict = dict(state.get("incidents", {}))
        labels_dict = dict(state.get("verification_labels", {}))

        for inc_id, inc_data in incidents_dict.items():
            inc = IncidentRecord(**inc_data) if isinstance(inc_data, dict) else inc_data
            verified_inc = self.process_incident(inc)
            incidents_dict[inc_id] = verified_inc.model_dump()
            labels_dict[inc_id] = verified_inc.verification_label.value

        state["incidents"] = incidents_dict
        state["verification_labels"] = labels_dict
        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
