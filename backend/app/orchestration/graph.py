"""LangGraph Multi-Agent Orchestration Workflow with StateGraph and Checkpointing."""
from __future__ import annotations
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from backend.app.agents.base.bus import MessageBus
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.situation import SituationAgent
from backend.app.agents.verification import VerificationAgent
from backend.app.agents.impact import ImpactAgent
from backend.app.agents.resource import ResourceAgent
from backend.app.agents.guardian import GuardianAgent
from backend.app.agents.command import CommandAgent
from backend.app.orchestration.state import DisasterState


class CrisisMeshOrchestrator:
    """Multi-Agent Orchestrator managing StateGraph execution, negotiation loops, and human approval."""

    def __init__(self, bus: Optional[MessageBus] = None, checkpointer: Optional[Any] = None):
        self.bus = bus or MessageBus()
        self.checkpointer = checkpointer or MemorySaver()

        # Instantiate the 7 agents sharing the common MessageBus
        self.supervisor = SupervisorAgent(bus=self.bus)
        self.situation = SituationAgent(bus=self.bus)
        self.verification = VerificationAgent(bus=self.bus)
        self.impact = ImpactAgent(bus=self.bus)
        self.resource = ResourceAgent(bus=self.bus, impact_engine=self.impact.engine)
        self.guardian = GuardianAgent(bus=self.bus)
        self.command = CommandAgent(bus=self.bus)

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(DisasterState)

        # 1. Register agent nodes
        builder.add_node("supervisor", self.supervisor.run)
        builder.add_node("situation", self.situation.run)
        builder.add_node("verification", self.verification.run)
        builder.add_node("impact", self.impact.run)
        builder.add_node("resource", self.resource.run)
        builder.add_node("impact_review", self._impact_review_step)
        builder.add_node("guardian", self.guardian.run)
        builder.add_node("command", self.command.run)
        builder.add_node("human_approval", self._human_approval_step)
        builder.add_node("dispatch", self._dispatch_step)

        # 2. Edges from START
        builder.add_edge(START, "supervisor")

        # 3. Conditional routing from Supervisor (Selective re-plan!)
        def supervisor_router(state: DisasterState) -> str:
            scheduled = state.get("scheduled_agents", [])
            if scheduled and scheduled[0] == "Resource":
                return "resource"
            elif scheduled and scheduled[0] == "Impact":
                return "impact"
            elif scheduled and scheduled[0] == "Guardian":
                return "guardian"
            return "situation"

        builder.add_conditional_edges(
            "supervisor",
            supervisor_router,
            {
                "situation": "situation",
                "impact": "impact",
                "resource": "resource",
                "guardian": "guardian"
            }
        )

        # 4. Situation -> Verification
        builder.add_edge("situation", "verification")

        # 5. Verification -> Clarification check
        def verification_router(state: DisasterState) -> str:
            msg_log = self.bus.get_trace()
            last_msg = msg_log[-1] if msg_log else None
            # If verification dispatched ClarificationRequest to Situation and not yet answered
            if last_msg and last_msg.type == "ClarificationRequest" and state.get("_clarification_loop_count", 0) < 1:
                state["_clarification_loop_count"] = state.get("_clarification_loop_count", 0) + 1
                return "situation"
            return "impact"

        builder.add_conditional_edges(
            "verification",
            verification_router,
            {"situation": "situation", "impact": "impact"}
        )

        # 6. Impact -> Resource
        builder.add_edge("impact", "resource")

        # 7. Resource -> Impact Review (VETO check)
        builder.add_edge("resource", "impact_review")

        # 8. Impact Review -> VETO loop condition (Max 3 rounds)
        def veto_router(state: DisasterState) -> str:
            pending_veto = state.get("pending_veto")
            veto_count = state.get("veto_count", 0)
            if pending_veto and veto_count < 3:
                return "resource"  # Re-solve under veto constraint
            return "guardian"

        builder.add_conditional_edges(
            "impact_review",
            veto_router,
            {"resource": "resource", "guardian": "guardian"}
        )

        # 9. Guardian -> Block or Command
        def guardian_router(state: DisasterState) -> str:
            if state.get("guardian_verdict") == "BLOCK":
                return END
            return "command"

        builder.add_conditional_edges(
            "guardian",
            guardian_router,
            {"command": "command", END: END}
        )

        # 10. Command -> Human Approval Interrupt -> Dispatch -> END
        builder.add_edge("command", "human_approval")
        builder.add_edge("human_approval", "dispatch")
        builder.add_edge("dispatch", END)

        # Compile with interrupt before human approval step and checkpointer
        return builder.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_approval"]
        )

    def _impact_review_step(self, state: DisasterState) -> DisasterState:
        """Impact agent inspects resource proposal and issues Veto if infeasible."""
        return self.impact.run(state)

    def _human_approval_step(self, state: DisasterState) -> DisasterState:
        """Interrupt point for Human Commander approval."""
        state["status"] = "AWAITING_COMMANDER_APPROVAL"
        return state

    def _dispatch_step(self, state: DisasterState) -> DisasterState:
        """Final execution step: dispatches units upon valid authorization."""
        state["status"] = "DISPATCHED"
        self.bus.publish(
            self.supervisor.send_message(
                receiver="Fleet",
                message_type="FleetDispatched",
                payload={"plan_id": state.get("current_plan", {}).get("plan_id", "unknown")}
            )
        )
        return state
