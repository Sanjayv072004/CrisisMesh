"""Comm Agent: Public Advisories and Unit Notifications."""
from __future__ import annotations
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.agents.base.llm_adapter import LLMAdapter, LLMMode
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import Plan, IncidentRecord

logger = logging.getLogger("CrisisMesh.CommAgent")


class CommAgent(BaseAgent):
    """Produces public advisories and dispatches notifications to units."""

    def __init__(self, bus: MessageBus, llm_adapter: Optional[LLMAdapter] = None):
        manifest = PermissionManifest(
            allowed_tools={"generate_public_advisory", "notify_units"},
            allowed_inbound={"CommanderBriefing", "StateSummary", "PlanApproved", "GuardianVerdict"},
            allowed_outbound={"PublicAdvisory", "UnitNotification"}
        )
        tools = {
            "generate_public_advisory": self.generate_public_advisory,
            "notify_units": self.notify_units,
        }
        super().__init__(name="Comm", role="Public Relations & Fleet Dispatcher", manifest=manifest, bus=bus, tools=tools)
        self.llm = llm_adapter or LLMAdapter(mode=LLMMode.MOCK)

    def generate_public_advisory(self, plan: Plan, incidents: Dict[str, IncidentRecord]) -> Dict[str, Any]:
        """Generate structured advisory based on plan and incidents."""
        # This acts as both the deterministic fallback and the structure the LLM would generate
        affected = [inc.title for inc in incidents.values()]

        # Determine highest severity
        max_sev = max((inc.severity for inc in incidents.values()), default=1)
        severity_level = "HIGH" if max_sev >= 4 else "MEDIUM" if max_sev == 3 else "LOW"

        # Get worst ETA
        max_eta = max((a.eta_minutes for a in plan.assignments), default=0.0)

        actions = [
            "Avoid low-lying areas and underpasses.",
            "Do not drive through flooded roads.",
        ]
        if max_sev >= 4:
            actions.append("Prepare for potential evacuation.")

        advisory = {
            "advisory_id": f"ADV-{plan.plan_id[:8]}",
            "title": f"Public Advisory: {len(incidents)} Incidents Reported",
            "severity_level": severity_level,
            "affected_areas": affected,
            "recommended_actions": actions,
            "estimated_response_minutes": round(max_eta, 1),
            "generated_by_llm": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return advisory

    def notify_units(self, plan: Plan) -> None:
        """Send notifications to units about their assignments."""
        for a in plan.assignments:
            self.send_message(
                receiver=f"Unit-{a.unit_id}",
                message_type="UnitNotification",
                payload={"assignment": a.model_dump()},
                trace_id="trace-comm"
            )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process plan into public advisories and notifications."""
        curr_plan_data = state.get("current_plan")
        incidents_data = state.get("incidents", {})

        if curr_plan_data and incidents_data:
            plan = Plan(**curr_plan_data)
            incidents = {k: IncidentRecord(**v) if isinstance(v, dict) else v for k, v in incidents_data.items()}

            advisory = self.call_tool("generate_public_advisory", plan=plan, incidents=incidents)
            state["public_advisory"] = advisory

            self.send_message(
                receiver="Public",
                message_type="PublicAdvisory",
                payload=advisory,
                trace_id="trace-comm"
            )

            self.call_tool("notify_units", plan=plan)

        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
