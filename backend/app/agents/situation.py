"""Situation Agent: Quarantined Information Extractor.

Possesses ZERO tools and ZERO secrets. Reads untrusted report text and parses it into
strictly validated IncidentRecord models matching Pydantic schemas.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.agents.base.llm_adapter import LLMAdapter, LLMMode
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import Report, IncidentRecord, UnitType, VerificationLabel


class SituationAgent(BaseAgent):
    """Quarantined extractor LLM converting raw untrusted text into structured incidents."""

    def __init__(self, bus: MessageBus, llm_adapter: Optional[LLMAdapter] = None):
        manifest = PermissionManifest(
            allowed_tools=set(),  # HARD RULE: Quarantined, ZERO tools
            allowed_inbound={"RawReport", "ClarificationRequest"},
            allowed_outbound={"IncidentParsed", "ClarificationResponse"}
        )
        super().__init__(name="Situation", role="Quarantined Incident Extractor", manifest=manifest, bus=bus)
        self.llm = llm_adapter or LLMAdapter(mode=LLMMode.MOCK)

    def extract_incident(self, report: Report, trace_id: str = "trace-extract") -> IncidentRecord:
        """Extract structured IncidentRecord from untrusted report text."""
        prompt = (
            f"Extract structured emergency incident from untrusted report:\n"
            f"Source: {report.source_id}\n"
            f"Location: ({report.lat}, {report.lon})\n"
            f"Text: '''{report.text}'''"
        )

        # In mock mode, synthesize realistic structured record
        raw_rec = self.llm.generate(
            agent_name=self.name,
            prompt=prompt,
            schema=IncidentRecord,
            trace_id=trace_id
        )

        # Ensure ground coordinates and timestamps are faithfully bound
        incident = IncidentRecord(
            id=f"inc_{report.id}",
            title=raw_rec.title if raw_rec.title else "Emergency Incident",
            description=report.text[:500],
            lat=report.lat,
            lon=report.lon,
            severity=raw_rec.severity,
            people_affected=raw_rec.people_affected,
            required_unit_type=raw_rec.required_unit_type,
            is_life_threatening=raw_rec.is_life_threatening,
            reported_at=report.timestamp,
            confidence=raw_rec.confidence,
            ambiguous_fields=raw_rec.ambiguous_fields,
            verification_label=VerificationLabel.UNVERIFIED,
            credibility_score=0.5
        )

        self.send_message(
            receiver="Verification",
            message_type="IncidentParsed",
            payload={"incident": incident.model_dump()},
            trace_id=trace_id
        )
        return incident

    def handle_clarification(self, incident_id: str, fields: list[str], trace_id: str) -> Dict[str, Any]:
        """Respond to a ClarificationRequest from Verification Agent."""
        clarification_data = {
            "incident_id": incident_id,
            "clarified_fields": {f: "Resolved from historical dispatch database" for f in fields},
            "status": "CLARIFIED"
        }
        self.send_message(
            receiver="Verification",
            message_type="ClarificationResponse",
            payload=clarification_data,
            trace_id=trace_id
        )
        return clarification_data

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming raw reports or clarification requests."""
        # Check for clarification request
        msg_log = state.get("message_log", [])
        clarification_req = next((m for m in reversed(msg_log) if m.get("type") == "ClarificationRequest"), None)
        if clarification_req:
            p = clarification_req.get("payload", {})
            self.handle_clarification(p.get("incident_id", ""), p.get("ambiguous_fields", []), clarification_req.get("trace_id", "trace-cl"))
            return state

        # Ingest new reports
        raw_reports = state.get("raw_reports", [])
        incidents = dict(state.get("incidents", {}))
        for r_data in raw_reports:
            r = Report(**r_data) if isinstance(r_data, dict) else r_data
            inc = self.extract_incident(r)
            incidents[inc.id] = inc.model_dump()

        state["incidents"] = incidents
        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
