"""CrisisMesh CLI: Scenario Runner and Demonstration Tool."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.models.schemas import Unit, IncidentRecord, Hospital, Plan, PlanDiff

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "scenario.json"


def run_scenario(auto_approve: bool = True):
    """Execute complete simulated emergency scenario from /data/scenario.json."""
    print("=" * 70)
    print("      CRISISMESH: MULTI-AGENT FLOOD CRISIS COORDINATION DEMO")
    print("      GATEWAYS 2026 - Domain 4: Crisis Command")
    print("=" * 70)

    # 1. Load synthetic scenario
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        scenario = json.load(f)

    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    # 2. Build T0 Initial State
    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "message_log": [],
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    config = {"configurable": {"thread_id": "bengaluru-flood-run-001"}}

    print("\n>>> INGESTING T0 EMERGENCY INCIDENTS...")
    print(f"Loaded {len(scenario['t0_incidents'])} incidents, {len(scenario['units'])} units, {len(scenario['hospitals'])} hospitals.")

    # 3. Run T0 Workflow until human approval interrupt
    state = orchestrator.graph.invoke(initial_state, config=config)

    print(f"\n[ORCHESTRATOR STATUS]: {state.get('status')}")
    plan_data = state.get("current_plan")
    if plan_data:
        plan = Plan(**plan_data)
        print("\n" + "-"*60)
        print(f"PROPOSED T0 PLAN (ID: {plan.plan_id[:8]})")
        print(f"Total Cost: {plan.cost_breakdown.total_cost:.2f} | Delay Harm: {plan.cost_breakdown.delay_harm_cost:.2f} | Wasted Cost: {plan.cost_breakdown.wasted_dispatch_cost:.2f}")
        for a in plan.assignments:
            prov = " [PROVISIONAL]" if a.is_provisional else " [CONFIRMED]"
            print(f"  * {a.unit_id} -> {a.incident_id} (ETA: {a.eta_minutes}m){prov}")
        print("-"*60)

    briefing = state.get("commander_briefing", {})
    if briefing:
        print("\n[COMMANDER BRIEFING]:")
        print(briefing.get("recommendation"))

    # 4. Human Approval Gate
    if auto_approve:
        print("\n>>> HUMAN COMMANDER APPROVAL: SIGNED (Auto-Approve for test/demo mode)")
        state["previous_approved_plan"] = state.get("current_plan")
        state["status"] = "APPROVED"
        # Resume graph from checkpointer past interrupt node
        state = orchestrator.graph.invoke(None, config=config)
        print(f"[FINAL T0 DISPATCH STATUS]: {state.get('status')}")

    # 5. T+10 Change Events (Selective Re-Plan)
    print("\n" + "="*70)
    print(">>> T+10 SCENARIO EVENT OCCURS:")
    print("    1. Critical Incident: SUV submerged in Outer Ring Road Underpass!")
    print("    2. Unit Breakdown: Ambulance 2 engine hydrostatic lock (UNAVAILABLE)")
    print("="*70)

    # Update state with T+10 events
    t10_incident = scenario["t10_change_events"][0]["incident"]
    state["incidents"][t10_incident["id"]] = t10_incident

    for u in state["units"]:
        if u["id"] == "amb_02":
            u["status"] = "unavailable"
        elif u["id"] in [a.unit_id for a in plan.assignments]:
            u["status"] = "en_route"
            u["current_target_id"] = next(a.incident_id for a in plan.assignments if a.unit_id == u["id"])

    # Trigger selective re-plan for unit_status_change
    state["trigger_event_type"] = "unit_status_change"
    state["active_agents"] = []

    # Run selective re-plan
    t10_config = {"configurable": {"thread_id": "bengaluru-flood-run-002"}}
    state_t10 = orchestrator.graph.invoke(state, config=t10_config)

    print("\n[SELECTIVE RE-PLAN COMPLETE]")
    print(f"Active Agents in Re-Plan: {state_t10.get('active_agents')}")

    diff_data = state_t10.get("plan_diff")
    if diff_data:
        diff = PlanDiff(**diff_data)
        print("\n" + "-"*60)
        print(f"PLAN REVISION DIFF: {diff.summary}")
        for c in diff.changes:
            dec = " [REQUIRES HUMAN CONFIRMATION]" if c.requires_human_decision else ""
            print(f"  * Unit {c.unit_id}: {c.from_incident_id} -> {c.to_incident_id} ({c.reason}){dec}")
        print("-"*60)

    # 6. Print Full Inter-Agent Audit Trace
    print("\n" + "="*70)
    print("              INTER-AGENT MESSAGE BUS AUDIT TRACE")
    print("="*70)
    trace = bus.get_trace()
    for idx, msg in enumerate(trace, 1):
        ts = msg.timestamp.strftime("%H:%M:%S")
        print(f"[{idx:02d}] {ts} | {msg.sender:12} -> {msg.receiver:12} | Type: {msg.type}")
    print("="*70 + "\n")
    return state_t10


if __name__ == "__main__":
    auto = "--auto-approve" in sys.argv or True
    run_scenario(auto_approve=auto)

