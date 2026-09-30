"""Impact Agent: Road Graph Analysis, Reachability Modeling & Veto Review."""
from __future__ import annotations
import math
from typing import Dict, List, Any, Optional
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import (
    Unit, IncidentRecord, Hospital, Plan, ImpactReport, Veto
)
from backend.app.engines.impact import ImpactEngine


class ImpactAgent(BaseAgent):
    """Monitors road disruptions, produces ImpactReports, and holds VETO authority over unfeasible plans."""

    def __init__(self, bus: MessageBus, impact_engine: Optional[ImpactEngine] = None):
        manifest = PermissionManifest(
            allowed_tools={"compute_travel_time", "travel_time_matrix", "generate_impact_report", "review_route"},
            allowed_inbound={"IncidentVerified", "RoadBlockedAlert", "PlanProposed"},
            allowed_outbound={"ImpactAssessed", "PlanVeto"}
        )
        self.engine = impact_engine or ImpactEngine(force_synthetic=True)
        tools = {
            "compute_travel_time": self.engine.compute_travel_time,
            "travel_time_matrix": self.engine.travel_time_matrix,
            "generate_impact_report": self.engine.generate_impact_report,
            "review_route": self.engine.review_route,
        }
        super().__init__(name="Impact", role="Road Graph & Cascading Impact Assessor", manifest=manifest, bus=bus, tools=tools)

    def review_plan(
        self, plan: Plan, units: List[Unit], incidents: List[IncidentRecord], max_eta_mins: float = 40.0, trace_id: str = "trace-review"
    ) -> Optional[Veto]:
        """Review proposed plan for unreachable or excessively delayed dispatches."""
        unit_map = {u.id: u for u in units}
        inc_map = {i.id: i for i in incidents}
        infeasible: list[tuple[str, str]] = []
        veto_reasons: list[str] = []

        for a in plan.assignments:
            u = unit_map.get(a.unit_id)
            inc = inc_map.get(a.incident_id)
            if not u or not inc:
                continue

            eta, _ = self.call_tool("compute_travel_time", trace_id=trace_id, start_lat=u.lat, start_lon=u.lon, end_lat=inc.lat, end_lon=inc.lon)

            if math.isinf(eta):
                infeasible.append((a.unit_id, a.incident_id))
                veto_reasons.append(f"Unit {u.id} cannot reach incident {inc.id}: route cut off by flooding")
            elif eta > max_eta_mins:
                infeasible.append((a.unit_id, a.incident_id))
                veto_reasons.append(f"Unit {u.id} arrival at {inc.id} takes {eta:.1f}m exceeding {max_eta_mins}m threshold")

        if infeasible:
            veto = Veto(
                reason="; ".join(veto_reasons),
                constraints=infeasible
            )
            self.send_message(
                receiver="Resource",
                message_type="PlanVeto",
                payload={"veto": veto.model_dump()},
                trace_id=trace_id
            )
            return veto

        return None

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall infrastructure impacts and evaluate current plan if proposed."""
        units_raw = state.get("units", [])
        incidents_raw = list(state.get("incidents", {}).values())
        hospitals_raw = state.get("hospitals", [])

        units = [Unit(**u) if isinstance(u, dict) else u for u in units_raw]
        incidents = [IncidentRecord(**i) if isinstance(i, dict) else i for i in incidents_raw]
        hospitals = [Hospital(**h) if isinstance(h, dict) else h for h in hospitals_raw]

        report = self.call_tool("generate_impact_report", units=units, incidents=incidents, hospitals=hospitals)
        state["impact_report"] = report.model_dump()

        # If a plan proposal is pending review, review it
        curr_plan_data = state.get("current_plan")
        if curr_plan_data and curr_plan_data.get("status") == "PROPOSED":
            plan = Plan(**curr_plan_data)
            veto = self.review_plan(plan, units, incidents)
            if veto:
                state["pending_veto"] = veto.model_dump()
                state["veto_count"] = state.get("veto_count", 0) + 1
            else:
                state["pending_veto"] = None

        self.send_message(
            receiver="Resource",
            message_type="ImpactAssessed",
            payload={"flooded_roads": report.flooded_roads, "isolated_incidents": report.isolated_incidents},
            trace_id="trace-impact"
        )
        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
