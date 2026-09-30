"""Supervisor Agent: Event Router, Selective Re-Planner & Negotiation Budget Manager."""
from __future__ import annotations
from typing import Dict, List, Any, Optional
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.security.manifest import PermissionManifest


class SupervisorAgent(BaseAgent):
    """Orchestrates event routing, triggers selective re-plans, and enforces step & negotiation budgets."""

    def __init__(self, bus: MessageBus, max_negotiation_rounds: int = 3, max_step_budget: int = 25):
        manifest = PermissionManifest(
            allowed_tools={"route_event", "check_budget"},
            allowed_inbound={"CrisisEvent", "GuardianVerdict", "PlanVeto"},
            allowed_outbound={"AgentTrigger", "WorkflowComplete", "BudgetExceeded", "FleetDispatched"}
        )
        tools = {
            "route_event": self.route_event,
            "check_budget": self.check_budget,
        }
        super().__init__(name="Supervisor", role="Workflow Coordinator & Selective Router", manifest=manifest, bus=bus, tools=tools)
        self.max_negotiation_rounds = max_negotiation_rounds
        self.max_step_budget = max_step_budget

    def route_event(self, event_type: str) -> List[str]:
        """Selective re-run mapping based on event category."""
        if event_type in ("unit_status_change", "commander_rejection"):
            # Selective re-plan: Only affected agents re-run!
            return ["Resource", "Guardian", "Command"]
        elif event_type in ("road_blocked", "road_block"):
            return ["Impact", "Resource", "Guardian", "Command"]
        elif event_type == "new_report":
            return ["Situation", "Verification", "Impact", "Resource", "Guardian", "Command"]
        elif event_type == "approval":
            return ["Dispatch"]
        elif event_type == "attack_flag":
            return ["Guardian"]
        else:
            return ["Situation", "Verification", "Impact", "Resource", "Guardian", "Command"]

    def check_budget(self, current_steps: int, veto_count: int) -> Tuple[bool, str]:
        """Enforce strict limits: max 3 negotiation rounds and finite step budget."""
        if veto_count >= self.max_negotiation_rounds:
            return False, f"Maximum negotiation rounds ({self.max_negotiation_rounds}) reached. Escalating to Commander."
        if current_steps >= self.max_step_budget:
            return False, f"Step budget of {self.max_step_budget} exhausted. Terminating loop."
        return True, "Budget within bounds"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supervisor routing logic."""
        steps = state.get("step_budget", 0) + 1
        veto_count = state.get("veto_count", 0)
        state["step_budget"] = steps

        is_ok, budget_reason = self.call_tool("check_budget", current_steps=steps, veto_count=veto_count)
        if not is_ok:
            state["status"] = "ESCALATED"
            state["error"] = budget_reason
            self.send_message(
                receiver="Guardian",
                message_type="BudgetExceeded",
                payload={"reason": budget_reason, "steps": steps, "vetoes": veto_count}
            )
            return state

        event_type = state.get("trigger_event_type", "new_report")
        target_agents = self.call_tool("route_event", event_type=event_type)
        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        state["scheduled_agents"] = target_agents
        return state


