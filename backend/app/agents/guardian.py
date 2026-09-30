"""Guardian Agent: Independent Security, Safety & Policy Gatekeeper."""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import Plan, SecurityEvent


class GuardianAgent(BaseAgent):
    """Reviews every agent output and proposed plan. Can ALLOW, BLOCK, or ESCALATE_TO_HUMAN."""

    def __init__(self, bus: MessageBus, max_unverified_fleet_share: float = 0.60):
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

    def validate_policy(self, plan: Plan) -> Tuple[str, str]:
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

        return "ALLOW", "All safety and allocation policies satisfied"

    def check_anomalies(self, plan: Plan) -> Tuple[str, str]:
        """Detect operational anomalies e.g. negative costs, invalid ETAs."""
        for a in plan.assignments:
            if a.eta_minutes < 0:
                return "BLOCK", f"Anomaly: Negative ETA ({a.eta_minutes}m) for unit {a.unit_id}"
            if a.cost < 0:
                return "BLOCK", f"Anomaly: Negative cost ({a.cost}) for assignment {a.incident_id}"
        return "ALLOW", "No anomalies detected"

    def review_proposed_plan(self, plan: Plan, trace_id: str = "trace-guard") -> Tuple[str, str]:
        """Review plan proposal and emit GuardianVerdict."""
        verdict, reason = self.call_tool("validate_policy", plan=plan)
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
        curr_plan_data = state.get("current_plan")
        if curr_plan_data:
            plan = Plan(**curr_plan_data)
            verdict, reason = self.review_proposed_plan(plan)
            state["guardian_verdict"] = verdict
            state["guardian_reason"] = reason

        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
