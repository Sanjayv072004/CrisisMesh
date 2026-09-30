"""Command Agent: Human Commander Briefing, Plan Diff Explanation & Counterfactuals."""
from __future__ import annotations
from typing import Dict, Any, Optional
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.bus import MessageBus
from backend.app.agents.base.llm_adapter import LLMAdapter, LLMMode
from backend.app.security.manifest import PermissionManifest
from backend.app.models.schemas import Plan, PlanDiff


class CommandAgent(BaseAgent):
    """Synthesizer LLM operating strictly on structured data (ZERO tools, NEVER receives raw reports)."""

    def __init__(self, bus: MessageBus, llm_adapter: Optional[LLMAdapter] = None):
        manifest = PermissionManifest(
            allowed_tools=set(),  # HARD RULE: Zero tools
            allowed_inbound={"GuardianVerdict", "PlanDiffReady", "StateSummary"},
            allowed_outbound={"CommanderBriefing"}
        )
        super().__init__(name="Command", role="Commander Briefing & Plan Explainer", manifest=manifest, bus=bus)
        self.llm = llm_adapter or LLMAdapter(mode=LLMMode.MOCK)

    def generate_briefing(self, plan: Plan, diff: Optional[PlanDiff] = None, trace_id: str = "trace-cmd") -> Dict[str, Any]:
        """Synthesize human commander recommendation, diff analysis, and why-not explanations."""
        # Build deterministic explanation from structured data
        recommendation_lines = [
            f"RECOMMENDATION: Dispatch plan {plan.plan_id[:8]} formulated with total cost {plan.cost_breakdown.total_cost:.2f}.",
            f"Active assignments: {len(plan.assignments)}, unserved incidents: {len(plan.unserved_incidents)}."
        ]

        # Provisional / Human decision flags
        provisional_items = [a for a in plan.assignments if a.is_provisional]
        if provisional_items:
            recommendation_lines.append(
                f"ATTENTION: {len(provisional_items)} assignment(s) are PROVISIONAL on unverified incidents and require your confirmation before physical deployment."
            )

        # Plan Diff Explanation
        diff_explanation = "Initial dispatch plan."
        if diff:
            diff_explanation = (
                f"PLAN REVISION DELTA: {diff.units_redirected} unit(s) redirected. Cost delta: {diff.total_cost_delta:+.2f}. "
                f"{'Requires commander authorization.' if diff.requires_human_decision else 'Standard operational shift.'}"
            )

        # Counterfactual Runner-Up Explanations
        counterfactuals = {}
        for inc_id, runner in plan.runner_up_per_incident.items():
            if runner.unit_id:
                counterfactuals[inc_id] = (
                    f"Runner-up unit {runner.unit_id} not chosen: {runner.reason_not_chosen}."
                )
            else:
                counterfactuals[inc_id] = f"No alternative unit available ({runner.reason_not_chosen})."

        briefing = {
            "plan_id": plan.plan_id,
            "recommendation": "\n".join(recommendation_lines),
            "diff_explanation": diff_explanation,
            "counterfactuals": counterfactuals,
            "requires_human_decision": any(a.is_provisional for a in plan.assignments) or (diff.requires_human_decision if diff else False),
        }

        self.send_message(
            receiver="Commander",
            message_type="CommanderBriefing",
            payload=briefing,
            trace_id=trace_id
        )
        return briefing

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process structured state into commander briefing."""
        # Safety invariant assertion: Command NEVER receives raw report text
        assert "raw_reports" not in state or state.get("_quarantined_raw_reports_isolated", True), \
            "CRITICAL INVARIANT VIOLATED: Command Agent received untrusted raw report text!"

        curr_plan_data = state.get("current_plan")
        if curr_plan_data:
            plan = Plan(**curr_plan_data)
            diff_data = state.get("plan_diff")
            diff = PlanDiff(**diff_data) if diff_data else None

            briefing = self.generate_briefing(plan, diff)
            state["commander_briefing"] = briefing

        state["active_agents"] = list(set(state.get("active_agents", [])) | {self.name})
        return state
