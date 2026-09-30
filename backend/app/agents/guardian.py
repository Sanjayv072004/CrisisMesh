"""Guardian Agent: Independent Security, Safety & Policy Gatekeeper."""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import Plan, SecurityEvent, IncidentRecord


class GuardianAgent(BaseAgent):
    """Reviews every agent output and proposed plan. Can ALLOW, BLOCK, or ESCALATE_TO_HUMAN."""

    def __init__(
        self,
        bus: MessageBus,
        max_unverified_fleet_share: float = 0.60,
        credibility_floor: float = 0.20,
    ):
        manifest = PermissionManifest(
            allowed_tools={"validate_policy", "check_anomalies"},
            allowed_inbound={"PlanProposed", "SecurityViolation", "ApprovalSigned"},
            allowed_outbound={"GuardianVerdict", "SecurityAlert"}
        )
        tools = {
            "validate_policy": self.validate_policy,
            "check_anomalies": self.check_anomalies,
        }
        super().__init__(name="Guardian", role="Independent Policy & Safety Sentry", manifest=manifest, bus=bus, tools=tools)
        self.max_unverified_fleet_share = max_unverified_fleet_share
        self.credibility_floor = credibility_floor

    def validate_policy(self, plan: Plan, incidents: Optional[List[IncidentRecord]] = None) -> Tuple[str, str]:
        """Verify policy constraints: double-booking, unverified fleet share, schema constraints."""
        # Rule 1: No unit double-booked
        assigned_units = [a.unit_id for a in plan.assignments]
        if len(assigned_units) != len(set(assigned_units)):
            duplicates = [u for u in assigned_units if assigned_units.count(u) > 1]
            return "BLOCK", f"Double-booking detected: unit(s) {duplicates} assigned to multiple incidents"

        # Rule 2: Unverified incidents must be marked provisional
        for a in plan.assignments:
            if a.cost > 20.0 and a.is_provisional and not a.requires_human_confirmation:
                return "BLOCK", f"Unverified incident assignment {a.incident_id} lacks human confirmation flag"

        # Rule 3: Fleet cap on low-credibility/unverified incidents
        if plan.assignments:
            provisional_count = sum(1 for a in plan.assignments if a.is_provisional)
            share = provisional_count / len(plan.assignments)
            if share > self.max_unverified_fleet_share:
                return "ESCALATE_TO_HUMAN", f"{share*100:.1f}% of fleet committed to unverified incidents (cap: {self.max_unverified_fleet_share*100}%)"

        # Rule 4: Credibility floor quarantine enforcement
        if incidents:
            inc_map = {i.id: i for i in incidents}
            for a in plan.assignments:
                inc = inc_map.get(a.incident_id)
                if inc and inc.credibility_score < self.credibility_floor:
                    return "BLOCK", f"Safety violation: Unit {a.unit_id} assigned to quarantined incident {a.incident_id} (credibility {inc.credibility_score:.4f} < floor {self.credibility_floor})"

        return "ALLOW", "All safety and allocation policies satisfied"

    def check_anomalies(self, plan: Plan) -> Tuple[str, str]:
        """Detect operational anomalies e.g. negative costs, invalid ETAs."""
        for a in plan.assignments:
            if a.eta_minutes < 0:
                return "BLOCK", f"Anomaly: Negative ETA ({a.eta_minutes}m) for unit {a.unit_id}"
            if a.cost < 0:
                return "BLOCK", f"Anomaly: Negative cost ({a.cost}) for assignment {a.incident_id}"
        return "ALLOW", "No anomalies detected"

    def review_proposed_plan(self, plan: Plan, incidents: Optional[List[IncidentRecord]] = None, trace_id: str = "trace-guard") -> Tuple[str, str]:
        """Review plan proposal and emit GuardianVerdict."""
        verdict, reason = self.call_tool("validate_policy", plan=plan, incidents=incidents)
        if verdict != "ALLOW":
            self._emit_verdict(verdict, reason, trace_id)
            return verdict, reason

        verdict_anom, reason_anom = self.call_tool("check_anomalies", plan=plan)
        if verdict_anom != "ALLOW":
            self._emit_verdict(verdict_anom, reason_anom, trace_id)
            return verdict_anom, reason_anom

        self._emit_verdict("ALLOW", "Plan approved for commander presentation", trace_id)
        return "ALLOW", "Plan approved"

    def _emit_verdict(self, verdict: str, reason: str, trace_id: str):
        self.send_message(
            receiver="Supervisor",
            message_type="GuardianVerdict",
            payload={"verdict": verdict, "reason": reason},
            trace_id=trace_id
        )
        if verdict == "BLOCK":
            sec_event = SecurityEvent(
                event_type="policy_block",
                severity="HIGH",
                agent_name=self.name,
                description=f"Guardian blocked plan: {reason}"
            )
            self.send_message(
                receiver="AuditStore",
                message_type="SecurityAlert",
                payload={"event": sec_event.model_dump()},
                trace_id=trace_id
            )

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect state proposals and post verdicts."""
        from backend.app.models.schemas import IncidentRecord
        incidents_raw = list(state.get("incidents", {}).values())
        incidents = [IncidentRecord(**i) if isinstance(i, dict) else i for i in incidents_raw]

        # Audit incidents below credibility floor and log security alerts
        for inc in incidents:
            if inc.credibility_score < self.credibility_floor:
                sec_event = SecurityEvent(
                    event_type="credibility_floor_quarantine",
                    severity="HIGH",
                    agent_name=self.name,
                    description=f"Incident {inc.id} quarantined: credibility {inc.credibility_score:.4f} is below floor {self.credibility_floor}. Excluded from dispatch.",
                    metadata={"incident_id": inc.id, "credibility": inc.credibility_score, "floor": self.credibility_floor}
                )
                self.send_message(
                    receiver="AuditStore",
                    message_type="SecurityAlert",
                    payload={"event": sec_event.model_dump()},
                    trace_id="trace-guard-floor"
                )

        curr_plan_data = state.get("current_plan")
        if curr_plan_data:
            plan = Plan(**curr_plan_data)
            verdict, reason = self.review_proposed_plan(plan, incidents=incidents)
            state["guardian_verdict"] = verdict
            state["guardian_reason"] = reason

        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
