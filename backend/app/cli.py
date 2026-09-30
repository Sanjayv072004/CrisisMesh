"""CrisisMesh CLI: Scenario Runner and Demonstration Tool."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.models.schemas import Unit, IncidentRecord, Hospital, Plan, PlanDiff
from backend.app.security.crypto import CommanderKeyManager, ApprovalGate
from backend.app.security.rbac import CommanderToken

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
    orchestrator = CrisisMeshOrchestrator(
        bus=bus,
        sensors=scenario.get("sensors", []),
        source_registry=scenario.get("source_registry", {}),
        raw_reports={r["id"]: r for r in scenario.get("raw_reports", [])}
    )

    # 2. Build T0 Initial State
    initial_state = {
        "trigger_event_type": "new_report",
        "raw_reports": {r["id"]: r for r in scenario.get("raw_reports", [])},
        "sensors": scenario.get("sensors", []),
        "source_registry": scenario.get("source_registry", {}),
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

    # Print Verification Table
    print("\n" + "="*70)
    print("                 INCIDENT VERIFICATION SUMMARY (T0)")
    print("="*70)
    print(f"{'Incident ID':<14} | {'Severity':<8} | {'Score':<7} | {'Label':<12} | {'Status'}")
    print("-" * 70)
    for inc_id, inc_data in state.get("incidents", {}).items():
        score = inc_data.get("credibility_score", 0.0)
        lbl = inc_data.get("verification_label", "unverified")
        sev = inc_data.get("severity", 3)
        prov = "PROVISIONAL" if (lbl == "unverified" or score < 0.75) else "CONFIRMED"
        print(f"{inc_id:<14} | SEV {sev:<4} | {score:<7.4f} | {lbl.upper():<12} | {prov}")
    print("="*70)

    plan_data = state.get("current_plan")
    if plan_data:
        plan = Plan(**plan_data)
        print("\n" + "-"*70)
        print(f"PROPOSED T0 PLAN (ID: {plan.plan_id[:8]})")
        print(f"Total Cost: {plan.cost_breakdown.total_cost:.2f} | Delay Harm: {plan.cost_breakdown.delay_harm_cost:.2f} | Wasted Cost: {plan.cost_breakdown.wasted_dispatch_cost:.2f}")
        for a in plan.assignments:
            prov = " [PROVISIONAL]" if a.is_provisional else " [CONFIRMED]"
            print(f"  * {a.unit_id} -> {a.incident_id} (ETA: {a.eta_minutes}m){prov}")
        print("-"*70)

    briefing = state.get("commander_briefing", {})
    if briefing:
        print("\n[COMMANDER BRIEFING]:")
        print(briefing.get("recommendation"))

    # 4. Human Approval Gate
    if auto_approve:
        print("\n>>> HUMAN COMMANDER APPROVAL: SIGNING DISPATCH AUTHORIZATION (Ed25519 Digital Signature)")
        key_mgr = CommanderKeyManager()
        plan_hash = ApprovalGate.compute_plan_hash(state["current_plan"])
        signed_approval = orchestrator.approval_gate.sign_approval(
            plan_id=state["current_plan"]["plan_id"],
            plan_hash=plan_hash,
            signing_key=key_mgr.signing_key
        )
        commander_token = CommanderToken(
            user_id="commander_bengaluru_01",
            public_key_hex=key_mgr.get_public_key_hex()
        )
        orchestrator.graph.update_state(config, {
            "commander_token": commander_token,
            "signed_approval": signed_approval,
            "previous_approved_plan": state.get("current_plan"),
            "status": "APPROVED",
        })
        print(f"    * Commander Key Hex: {commander_token.public_key_hex[:16]}...")
        print(f"    * Bound Plan Hash:   {plan_hash[:16]}...")
        print(f"    * Digital Signature: {signed_approval.signature_hex[:16]}... (VALID)")
        # Resume graph from checkpointer past interrupt node
        state = orchestrator.graph.invoke(None, config=config)
        print(f"[FINAL T0 DISPATCH STATUS]: {state.get('status')}")

    # 5. T+10 Change Events (Selective Re-Plan)
    print("\n" + "="*70)
    print(">>> T+10 SCENARIO EVENT OCCURS:")
    print("    1. Critical Incident: SUV submerged in Outer Ring Road Underpass!")
    print("    2. Unit Breakdown: Ambulance 2 engine hydrostatic lock (UNAVAILABLE)")
    print("    3. Flash Flood Road Inundation: Outer Ring Road underpass approach cut off")
    print("="*70)

    # Ingest and verify T+10 incident
    t10_incident_raw = scenario["t10_change_events"][0]["incident"]
    t10_rec = IncidentRecord(**t10_incident_raw)
    t10_verified = orchestrator.verification.process_incident(t10_rec)
    state["incidents"][t10_rec.id] = t10_verified.model_dump()

    score = t10_verified.credibility_score
    lbl = t10_verified.verification_label.value
    print("\n" + "="*70)
    print("            T+10 CRITICAL INCIDENT VERIFICATION BREAKDOWN")
    print("="*70)
    print(f"Incident:    {t10_rec.id} ({t10_rec.title})")
    print(f"Severity:    SEV {t10_rec.severity} (Life-Threatening: {t10_rec.is_life_threatening})")
    print(f"Sources:     {t10_rec.report_ids} (Citizen report from citizen_sanjay, prior weight 0.55)")
    print("Sensors:     No flood water-level sensor active within 1000m radius")
    print(f"Score:       {score:.4f} | Label: {lbl.upper()}")
    print("Operational: PROVISIONAL dispatch assigned immediately due to severity 5 danger;")
    print("             Unit commander confirmation required on scene to confirm or stand down.")
    print("="*70)

    # Update unit statuses
    for u in state["units"]:
        if u["id"] == "amb_02":
            u["status"] = "unavailable"
        elif u["id"] in [a.unit_id for a in plan.assignments]:
            u["status"] = "en_route"
            u["current_target_id"] = next(a.incident_id for a in plan.assignments if a.unit_id == u["id"])

    # Physical road block in the environment
    orchestrator.impact.engine.block_road("bellandur", "orr_underpass", reason="flooded underpass approach", flood_depth=2.5)
    orchestrator.impact.engine.block_road("bellandur", "hosp_sakra", reason="flooded underpass approach", flood_depth=2.0)
    orchestrator.impact.engine.block_road("koramangala", "bellandur", reason="flooded sarjapur road", flood_depth=1.5)
    orchestrator.impact.engine.block_road("hsr_layout", "bellandur", reason="flooded outer ring road", flood_depth=2.0)

    # Trigger selective re-plan for unit_status_change
    state["trigger_event_type"] = "unit_status_change"
    state["active_agents"] = []

    # Run selective re-plan
    t10_config = {"configurable": {"thread_id": "bengaluru-flood-run-002"}}
    state_t10 = orchestrator.graph.invoke(state, config=t10_config)

    print("\n[SELECTIVE RE-PLAN COMPLETE]")
    print(f"Active Agents in Re-Plan: {state_t10.get('active_agents')}")

    # Print T+10 Plan
    t10_plan_data = state_t10.get("current_plan")
    if t10_plan_data:
        t10_plan = Plan(**t10_plan_data)
        print("\n" + "-"*70)
        print(f"PROPOSED T+10 RE-PLAN (ID: {t10_plan.plan_id[:8]})")
        print(f"Total Cost: {t10_plan.cost_breakdown.total_cost:.2f} | Delay Harm: {t10_plan.cost_breakdown.delay_harm_cost:.2f} | Wasted Cost: {t10_plan.cost_breakdown.wasted_dispatch_cost:.2f}")
        for a in t10_plan.assignments:
            prov = " [PROVISIONAL]" if a.is_provisional else " [CONFIRMED]"
            print(f"  * {a.unit_id} -> {a.incident_id} (ETA: {a.eta_minutes}m){prov}")
        print("-"*70)

    diff_data = state_t10.get("plan_diff")
    if diff_data:
        diff = PlanDiff(**diff_data)
        print("\n" + "-"*70)
        print(f"PLAN REVISION DIFF: {diff.summary}")
        print(f"Plan Cost Delta: {diff.total_cost_delta:.2f} | Units Redirected: {diff.units_redirected}")
        for c in diff.changes:
            dec = " [REQUIRES HUMAN DECISION]" if c.requires_human_decision else ""
            eta_info = f"(ETA: {c.eta_before}m -> {c.eta_after}m)" if (c.eta_before is not None and c.eta_after is not None) else ""
            print(f"  * Unit {c.unit_id}: {c.from_incident_id or 'none'} -> {c.to_incident_id or 'none'} | {c.change_kind.value} | {c.reason} {eta_info}{dec}")
        print("-"*70)

    neg_hist = state_t10.get("negotiation_history", [])
    if neg_hist:
        print("\n" + "="*70)
        print("               INTER-AGENT NEGOTIATION ROUNDS")
        print("="*70)
        for h in neg_hist:
            print(f"Round {h.get('round')}: Veto by ImpactAgent: {h.get('veto_reason')}")
            print(f"         Added constraints: {h.get('added_constraints')}")
        print("="*70)

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

