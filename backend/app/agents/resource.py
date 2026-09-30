"""Resource Agent: Deterministic CP-SAT Allocation Solver & Negotiator."""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Set, Tuple
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import (
    Unit, IncidentRecord, Plan, PlanDiff, Veto
)
from backend.app.engines.allocation import AllocationEngine, AllocationConfig
from backend.app.engines.impact import ImpactEngine


class ResourceAgent(BaseAgent):
    """Proposes resource allocation plans via CP-SAT and re-solves on Impact VETOs."""

    def __init__(self, bus: MessageBus, solver: Optional[AllocationEngine] = None, impact_engine: Optional[ImpactEngine] = None):
        manifest = PermissionManifest(
            allowed_tools={"solve_plan", "diff_plans"},
            allowed_inbound={"ImpactAssessed", "PlanVeto", "UnitStatusChanged"},
            allowed_outbound={"PlanProposed"}
        )
        self.solver = solver or AllocationEngine(AllocationConfig())
        self.impact = impact_engine or ImpactEngine(force_synthetic=True)
        tools = {
            "solve_plan": self.solver.solve,
            "diff_plans": self.solver.diff_plans,
        }
        super().__init__(name="Resource", role="CP-SAT Allocation Solver", manifest=manifest, bus=bus, tools=tools)
        self.forbidden_constraints: Set[Tuple[str, str]] = set()

    def propose_plan(
        self,
        incidents: List[IncidentRecord],
        units: List[Unit],
        previous_plan: Optional[Plan] = None,
        trace_id: str = "trace-res"
    ) -> Plan:
        """Formulate allocation plan using CP-SAT solver."""
        matrix = self.impact.travel_time_matrix(units, incidents)
        plan: Plan = self.call_tool(
            "solve_plan",
            trace_id=trace_id,
            incidents=incidents,
            units=units,
            travel_time_matrix=matrix,
            previous_plan=previous_plan,
            forbidden_pairs=self.forbidden_constraints
        )

        self.send_message(
            receiver="Guardian",
            message_type="PlanProposed",
            payload={"plan": plan.model_dump()},
            trace_id=trace_id
        )
        return plan

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CP-SAT solve or re-solve with newly received VETO constraints."""
        units_raw = state.get("units", [])
        incidents_raw = list(state.get("incidents", {}).values())
        units = [Unit(**u) if isinstance(u, dict) else u for u in units_raw]
        incidents = [IncidentRecord(**i) if isinstance(i, dict) else i for i in incidents_raw]

        prev_plan_raw = state.get("previous_approved_plan")
        prev_plan = Plan(**prev_plan_raw) if prev_plan_raw else None

        # Check for pending veto from Impact
        pending_veto = state.get("pending_veto")
        if pending_veto:
            veto = Veto(**pending_veto)
            for pair in veto.constraints:
                self.forbidden_constraints.add(tuple(pair))

            # Record negotiation history
            history = list(state.get("negotiation_history", []))
            history.append({
                "round": state.get("veto_count", 1),
                "veto_reason": veto.reason,
                "added_constraints": veto.constraints
            })
            state["negotiation_history"] = history
            state["pending_veto"] = None

        plan = self.propose_plan(incidents, units, previous_plan=prev_plan)
        state["current_plan"] = plan.model_dump()

        if prev_plan:
            diff: PlanDiff = self.call_tool("diff_plans", old_plan=prev_plan, new_plan=plan)
            state["plan_diff"] = diff.model_dump()

        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
