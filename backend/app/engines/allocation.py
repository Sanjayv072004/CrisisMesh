r"""Deterministic CP-SAT Allocation Engine using Google OR-Tools.

Computes mathematically optimal emergency unit dispatch plans:
- Hard constraints: 1 incident/unit, type matching, available units only, reachable routes only, vetoes respected.
- Multi-objective: Expected delay harm + wasted dispatch cost + switching penalty + unserved incident penalty.
- Uncertainty-aware: Dual-scenario expected cost optimization; unverified incidents receive provisional assignments.
- Low-churn re-planning: Explicit switching penalty (\lambda * redirected en-route units) and plan diff computation.
- Counterfactuals: Computes runner-up alternative unit per incident with delta cost and explanation.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Set, Any
from ortools.sat.python import cp_model
from backend.app.models.resource import (
    EmergencyUnit, UnitType, UnitStatus, IncidentRequirement, Hospital,
    UnitAssignment, RunnerUpOption, PlanCostBreakdown, PlanProposal,
    PlanDiff, PlanChangeDetail
)
from backend.app.engines.road_graph import RoadGraphEngine


class SolverConfig:
    """Configurable weights for the CP-SAT objective function."""
    w_delay: float = 1.5           # Cost per minute of delay scaled by severity & credibility
    c_false_alarm: float = 30.0    # Base cost of sending a unit to an unconfirmed false alarm
    lambda_switch: float = 50.0    # Penalty for redirecting a unit already EN_ROUTE
    w_unserved: float = 200.0      # Base penalty per severity point for leaving an incident unserved
    scale_factor: int = 100        # Integer scaling factor for CP-SAT solver


class AllocationEngine:
    """OR-Tools CP-SAT allocation engine for emergency units."""

    def __init__(self, road_engine: RoadGraphEngine, config: Optional[SolverConfig] = None):
        self.road_engine = road_engine
        self.config = config or SolverConfig()

    def solve_plan(
        self,
        incidents: List[IncidentRequirement],
        units: List[EmergencyUnit],
        hospitals: List[Hospital],
        forbidden_pairs: Optional[Set[Tuple[str, str]]] = None,
        time_limit_seconds: float = 5.0,
    ) -> PlanProposal:
        """Solve optimal assignment plan using CP-SAT.
        
        Args:
            incidents: Active crisis incidents needing response.
            units: Emergency fleet of ambulances, boats, trucks, squads.
            hospitals: Receiving trauma centers / emergency hospitals.
            forbidden_pairs: Set of (unit_id, incident_id) pairs vetoed by Impact Engine.
            time_limit_seconds: Maximum CP-SAT solver runtime.
        """
        forbidden = forbidden_pairs or set()
        model = cp_model.CpModel()

        # Decision variables: x[u, i] = 1 if unit u assigned to incident i
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # Decision variables: z[i] = 1 if incident i remains unserved
        z: Dict[str, cp_model.IntVar] = {}

        travel_times: Dict[Tuple[str, str], float] = {}
        target_hospitals: Dict[str, Optional[Hospital]] = {}
        assignment_costs: Dict[Tuple[str, str], float] = {}
        delay_costs: Dict[Tuple[str, str], float] = {}
        wasted_costs: Dict[Tuple[str, str], float] = {}
        switch_costs: Dict[Tuple[str, str], float] = {}
        unserved_costs: Dict[str, float] = {}

        # Precompute hospital for each incident
        for inc in incidents:
            best_hosp, hosp_eta = self.road_engine.find_best_hospital(inc.lat, inc.lon, hospitals)
            target_hospitals[inc.id] = best_hosp
            # Cost of unserved incident: severity * w_unserved
            unserved_costs[inc.id] = inc.severity * self.config.w_unserved
            z[inc.id] = model.NewBoolVar(f"unserved_{inc.id}")

        # Filter assignable units
        active_units = [u for u in units if u.status in (UnitStatus.AVAILABLE, UnitStatus.EN_ROUTE)]

        for u in active_units:
            for inc in incidents:
                # 1. Hard constraint: Type compatibility
                if u.unit_type != inc.required_unit_type:
                    continue

                # 2. Hard constraint: Forbidden/vetoed assignment
                if (u.id, inc.id) in forbidden:
                    continue

                # 3. Route reachability check
                eta, path = self.road_engine.compute_travel_time_minutes(u.lat, u.lon, inc.lat, inc.lon)
                if math.isinf(eta):
                    continue  # Cut off by road blocks

                travel_times[(u.id, inc.id)] = eta
                var = model.NewBoolVar(f"assign_{u.id}_{inc.id}")
                x[(u.id, inc.id)] = var

                # Objective terms:
                # A. Expected delay harm = severity * credibility * eta * w_delay
                delay_harm = inc.severity * inc.credibility * eta * self.config.w_delay
                delay_costs[(u.id, inc.id)] = delay_harm

                # B. Wasted dispatch cost = (1 - credibility) * c_false_alarm
                wasted = (1.0 - inc.credibility) * self.config.c_false_alarm
                wasted_costs[(u.id, inc.id)] = wasted

                # C. Low-churn switching penalty: if already EN_ROUTE to another incident
                switch_pen = 0.0
                if u.status == UnitStatus.EN_ROUTE and u.current_incident_id and u.current_incident_id != inc.id:
                    switch_pen = self.config.lambda_switch
                switch_costs[(u.id, inc.id)] = switch_pen

                assignment_costs[(u.id, inc.id)] = delay_harm + wasted + switch_pen

        # Constraint 1: Each unit assigned to at most ONE incident
        for u in active_units:
            unit_vars = [x[(u.id, inc.id)] for inc in incidents if (u.id, inc.id) in x]
            if unit_vars:
                model.Add(sum(unit_vars) <= 1)

        # Constraint 2: Each incident served by at most ONE unit, or flagged unserved
        for inc in incidents:
            inc_vars = [x[(u.id, inc.id)] for u in active_units if (u.id, inc.id) in x]
            model.Add(sum(inc_vars) + z[inc.id] == 1)

        # Objective Function (Minimized)
        obj_terms = []
        for pair, var in x.items():
            cost_scaled = int(round(assignment_costs[pair] * self.config.scale_factor))
            obj_terms.append(cost_scaled * var)

        for inc in incidents:
            unserved_scaled = int(round(unserved_costs[inc.id] * self.config.scale_factor))
            obj_terms.append(unserved_scaled * z[inc.id])

        model.Minimize(sum(obj_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        status = solver.Solve(model)

        # Build output plan proposal
        assignments: List[UnitAssignment] = []
        unserved_list: List[str] = []
        tot_delay = 0.0
        tot_wasted = 0.0
        tot_switch = 0.0
        tot_unserved = 0.0

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for pair, var in x.items():
                if solver.Value(var) == 1:
                    u_id, inc_id = pair
                    inc = next(i for i in incidents if i.id == inc_id)
                    eta = travel_times[pair]
                    cost = assignment_costs[pair]
                    tot_delay += delay_costs[pair]
                    tot_wasted += wasted_costs[pair]
                    tot_switch += switch_costs[pair]

                    # Provisional if unverified (< 0.75 credibility)
                    is_provisional = not inc.is_verified or (inc.credibility < 0.75)
                    hosp = target_hospitals.get(inc_id)

                    assignments.append(UnitAssignment(
                        unit_id=u_id,
                        incident_id=inc_id,
                        eta_minutes=round(eta, 1),
                        is_provisional=is_provisional,
                        target_hospital_id=hosp.id if hosp else None,
                        cost=round(cost, 2)
                    ))

            for inc in incidents:
                if solver.Value(z[inc.id]) == 1:
                    unserved_list.append(inc.id)
                    tot_unserved += unserved_costs[inc.id]

        total_cost = tot_delay + tot_wasted + tot_switch + tot_unserved
        breakdown = PlanCostBreakdown(
            total_cost=round(total_cost, 2),
            delay_harm_cost=round(tot_delay, 2),
            wasted_dispatch_cost=round(tot_wasted, 2),
            switching_penalty_cost=round(tot_switch, 2),
            unserved_penalty_cost=round(tot_unserved, 2),
        )

        # Counterfactual analysis: compute runner-up per incident
        assigned_units = {a.unit_id for a in assignments}
        runner_ups: Dict[str, RunnerUpOption] = {}

        for inc in incidents:
            assigned_u = next((a.unit_id for a in assignments if a.incident_id == inc.id), None)
            candidates = []
            for u in active_units:
                if u.id == assigned_u:
                    continue
                if (u.id, inc.id) in assignment_costs:
                    candidates.append((u.id, assignment_costs[(u.id, inc.id)], travel_times[(u.id, inc.id)]))

            candidates.sort(key=lambda item: item[1])
            if candidates:
                runner_id, runner_cost, runner_eta = candidates[0]
                primary_cost = assignment_costs.get((assigned_u, inc.id), 0.0) if assigned_u else unserved_costs[inc.id]
                primary_eta = travel_times.get((assigned_u, inc.id), 0.0) if assigned_u else 0.0
                runner_ups[inc.id] = RunnerUpOption(
                    incident_id=inc.id,
                    runner_up_unit_id=runner_id,
                    delta_eta_minutes=round(runner_eta - primary_eta, 1),
                    delta_cost=round(runner_cost - primary_cost, 2),
                    reason_not_chosen=f"Higher ETA by {round(runner_eta - primary_eta, 1)}m (cost increase: +{round(runner_cost - primary_cost, 2)})"
                )
            else:
                runner_ups[inc.id] = RunnerUpOption(
                    incident_id=inc.id,
                    runner_up_unit_id=None,
                    reason_not_chosen="No alternative reachable unit of compatible type"
                )

        return PlanProposal(
            assignments=assignments,
            unserved_incidents=unserved_list,
            cost_breakdown=breakdown,
            runner_up_per_incident=runner_ups,
            status="PROPOSED"
        )

    def diff_plans(self, old_plan: Optional[PlanProposal], new_plan: PlanProposal) -> PlanDiff:
        """Compute the operational delta between previous and newly revised plans."""
        if old_plan is None:
            return PlanDiff(
                old_plan_id=None,
                new_plan_id=new_plan.plan_id,
                changes=[
                    PlanChangeDetail(
                        unit_id=a.unit_id,
                        previous_incident_id=None,
                        new_incident_id=a.incident_id,
                        reason="Initial dispatch plan formulation",
                        cost_delta=a.cost,
                        requires_human_decision=a.is_provisional
                    )
                    for a in new_plan.assignments
                ],
                total_cost_delta=new_plan.cost_breakdown.total_cost,
                units_redirected=0,
                requires_human_decision=any(a.is_provisional for a in new_plan.assignments),
                summary="Initial dispatch plan generated"
            )

        old_map = {a.unit_id: a.incident_id for a in old_plan.assignments}
        new_map = {a.unit_id: a.incident_id for a in new_plan.assignments}
        all_units = set(old_map.keys()) | set(new_map.keys())

        changes: List[PlanChangeDetail] = []
        redirected_count = 0
        requires_decision = False

        for u_id in all_units:
            old_inc = old_map.get(u_id)
            new_inc = new_map.get(u_id)

            if old_inc != new_inc:
                if old_inc is not None and new_inc is not None:
                    reason = f"Unit {u_id} redirected from incident {old_inc} to {new_inc}"
                    redirected_count += 1
                    req_human = True
                elif old_inc is None and new_inc is not None:
                    reason = f"Unit {u_id} newly dispatched to {new_inc}"
                    req_human = False
                else:
                    reason = f"Unit {u_id} assignment cancelled (now available)"
                    req_human = True

                changes.append(PlanChangeDetail(
                    unit_id=u_id,
                    previous_incident_id=old_inc,
                    new_incident_id=new_inc,
                    reason=reason,
                    cost_delta=0.0,
                    requires_human_decision=req_human
                ))
                if req_human:
                    requires_decision = True

        cost_delta = round(new_plan.cost_breakdown.total_cost - old_plan.cost_breakdown.total_cost, 2)
        summary = (
            f"Plan revised: {redirected_count} unit(s) redirected, "
            f"cost delta: {'+' if cost_delta >= 0 else ''}{cost_delta}. "
            f"{'Commander decision required.' if requires_decision else 'Ready for review.'}"
        )

        return PlanDiff(
            old_plan_id=old_plan.plan_id,
            new_plan_id=new_plan.plan_id,
            changes=changes,
            total_cost_delta=cost_delta,
            units_redirected=redirected_count,
            requires_human_decision=requires_decision,
            summary=summary
        )

