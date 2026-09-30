"""Allocation Engine using Google OR-Tools CP-SAT.

Implements:
- Hard constraints: 1 incident/unit, unavailable units excluded, unit-type matching, reachable routes.
- Multi-objective: Expected delay harm + wasted dispatch cost + switching penalty + unserved penalty.
- Uncertainty-aware dual-scenario evaluation: For unverified incidents, optimizes expected cost across
  "report true" (p = credibility) and "report false" (1 - p). Assigns provisional tags.
- Naive baseline mode: Disables credibility weighting (p=1.0) and lambda=0 for benchmark comparisons.
- Counterfactual runner-up options with delta costs and delta ETAs.
- Low-churn re-planning: diff_plans(old, new) with per-change rationale, cost of change, and decision flags.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Set, Any
from ortools.sat.python import cp_model
from backend.app.models.schemas import (
    Unit, UnitType, UnitStatus, IncidentRecord, Hospital,
    Assignment, RunnerUp, PlanCost, Plan, PlanChange, PlanDiff, VerificationLabel, ChangeKind
)


class AllocationConfig:
    """Configurable weights for the CP-SAT objective function."""
    def __init__(
        self,
        severity_weight: float = 2.0,       # Delay harm multiplier per severity point per minute
        false_alarm_cost: float = 40.0,     # Cost penalty for dispatching to a false alarm
        lambda_switch: float = 60.0,        # Switching penalty for redirecting an EN_ROUTE unit
        unserved_penalty: float = 250.0,    # Base penalty per severity point for leaving incident unserved
        scale_factor: int = 100,            # Scaling factor for CP-SAT integer programming
        is_naive_baseline: bool = False,    # If True, ignores credibility (p=1.0) and sets lambda=0
        credibility_floor: float = 0.20,    # Incidents below this floor receive NO assignment
    ):
        self.severity_weight = severity_weight
        self.false_alarm_cost = 0.0 if is_naive_baseline else false_alarm_cost
        self.lambda_switch = 0.0 if is_naive_baseline else lambda_switch
        self.unserved_penalty = unserved_penalty
        self.scale_factor = scale_factor
        self.is_naive_baseline = is_naive_baseline
        self.credibility_floor = credibility_floor


class AllocationEngine:
    """Deterministic CP-SAT allocation engine for emergency fleet coordination."""

    def __init__(self, *args, **kwargs):
        config = None
        for a in args:
            if isinstance(a, AllocationConfig):
                config = a
        if "config" in kwargs:
            config = kwargs["config"]
        self.config = config or AllocationConfig()

    solve_plan = None  # defined below
    def solve(
        self,
        incidents: List[IncidentRecord],
        units: List[Unit],
        travel_time_matrix: Optional[Dict[Tuple[str, str], float]] = None, hospitals: Optional[List[Any]] = None,
        previous_plan: Optional[Plan] = None,
        forbidden_pairs: Optional[Set[Tuple[str, str]]] = None,
        time_limit_seconds: float = 5.0,
    ) -> Plan:
        """Solve optimal resource assignment plan via CP-SAT."""
        forbidden = forbidden_pairs or set()
        model = cp_model.CpModel()
        if travel_time_matrix is None:
            travel_time_matrix = {}
            from backend.app.engines.verification import haversine_distance_km
            for u in units:
                for inc in incidents:
                    d = haversine_distance_km(u.lat, u.lon, inc.lat, inc.lon)
                    travel_time_matrix[(u.id, inc.id)] = max(1.0, (d / 25.0) * 60.0)

        # Decision variables: x[u, i] = 1 if unit u assigned to incident i
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # Decision variables: z[i] = 1 if incident i is unserved
        z: Dict[str, cp_model.IntVar] = {}

        delay_costs: Dict[Tuple[str, str], float] = {}
        wasted_costs: Dict[Tuple[str, str], float] = {}
        switch_costs: Dict[Tuple[str, str], float] = {}
        total_assign_costs: Dict[Tuple[str, str], float] = {}
        unserved_costs: Dict[str, float] = {}

        # 1. Filter assignable incidents by credibility floor
        assignable_incidents = [
            inc for inc in incidents
            if self.config.is_naive_baseline or getattr(inc, "credibility_score", 0.5) >= self.config.credibility_floor
        ]

        # Unserved incident variables & costs
        for inc in incidents:
            z[inc.id] = model.NewBoolVar(f"unserved_{inc.id}")
            # In uncertainty-aware mode, expected unserved cost is p * (severity * penalty)
            p = 1.0 if self.config.is_naive_baseline else getattr(inc, "credibility_score", getattr(inc, "credibility", 0.5))
            unserved_costs[inc.id] = p * inc.severity * self.config.unserved_penalty

        # 2. Filter available units (HARD CONSTRAINT: Unavailable units never assigned)
        assignable_units = [u for u in units if u.status != UnitStatus.UNAVAILABLE]

        # Map previous assignments to detect redirected units
        prev_assignments: Dict[str, str] = {}
        if previous_plan:
            prev_assignments = {a.unit_id: a.incident_id for a in previous_plan.assignments}

        # 3. Create assignment variables and cost terms
        for u in assignable_units:
            for inc in assignable_incidents:
                # HARD CONSTRAINT: Unit type must match requirement
                if u.unit_type != inc.required_unit_type:
                    continue

                # HARD CONSTRAINT: Forbidden / vetoed assignments
                if (u.id, inc.id) in forbidden:
                    continue

                # HARD CONSTRAINT: Reachable routes only
                eta = travel_time_matrix.get((u.id, inc.id), float("inf"))
                if math.isinf(eta):
                    continue

                var = model.NewBoolVar(f"assign_{u.id}_{inc.id}")
                x[(u.id, inc.id)] = var

                # Probabilistic scenario evaluation:
                p = 1.0 if self.config.is_naive_baseline else getattr(inc, "credibility_score", getattr(inc, "credibility", 0.5))

                # (a) Expected delay harm: p * (severity * eta * severity_weight)
                delay_harm = p * (inc.severity * eta * self.config.severity_weight)
                delay_costs[(u.id, inc.id)] = delay_harm

                # (b) Wasted dispatch cost: (1 - p) * false_alarm_cost
                wasted = (1.0 - p) * self.config.false_alarm_cost
                wasted_costs[(u.id, inc.id)] = wasted

                # (c) Switching penalty: lambda * 1 if unit already en_route and redirected
                switch_pen = 0.0
                curr_target = getattr(u, "current_target_id", getattr(u, "current_incident_id", None)) or prev_assignments.get(u.id)
                if (u.status == UnitStatus.EN_ROUTE or u.id in prev_assignments) and curr_target and curr_target != inc.id:
                    switch_pen = self.config.lambda_switch
                switch_costs[(u.id, inc.id)] = switch_pen

                total_assign_costs[(u.id, inc.id)] = delay_harm + wasted + switch_pen

        # HARD CONSTRAINT: At most one incident per unit
        for u in assignable_units:
            unit_vars = [x[(u.id, inc.id)] for inc in incidents if (u.id, inc.id) in x]
            if unit_vars:
                model.Add(sum(unit_vars) <= 1)

        # HARD CONSTRAINT: Each incident served by at most one unit, or marked unserved
        for inc in incidents:
            inc_vars = [x[(u.id, inc.id)] for u in assignable_units if (u.id, inc.id) in x]
            model.Add(sum(inc_vars) + z[inc.id] == 1)

        # OBJECTIVE: Minimize scaled total cost
        obj_terms = []
        for pair, var in x.items():
            cost_int = int(round(total_assign_costs[pair] * self.config.scale_factor))
            obj_terms.append(cost_int * var)

        for inc in incidents:
            unserved_int = int(round(unserved_costs[inc.id] * self.config.scale_factor))
            obj_terms.append(unserved_int * z[inc.id])

        model.Minimize(sum(obj_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        status = solver.Solve(model)

        # Extract solution
        assignments: List[Assignment] = []
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
                    eta = travel_time_matrix[(u_id, inc_id)]
                    cost = total_assign_costs[pair]
                    tot_delay += delay_costs[pair]
                    tot_wasted += wasted_costs[pair]
                    tot_switch += switch_costs[pair]

                    # UNCERTAINTY-AWARE: Unverified incidents get PROVISIONAL assignments
                    is_prov = (getattr(inc, "verification_label", None) == VerificationLabel.UNVERIFIED) or (getattr(inc, "credibility_score", getattr(inc, "credibility", 0.5)) < 0.75)

                    assignments.append(Assignment(
                        unit_id=u_id,
                        incident_id=inc_id,
                        eta_minutes=round(eta, 1),
                        is_provisional=is_prov,
                        requires_human_confirmation=is_prov,
                        cost=round(cost, 2)
                    ))

            for inc in incidents:
                if solver.Value(z[inc.id]) == 1:
                    unserved_list.append(inc.id)
                    tot_unserved += unserved_costs[inc.id]

        total_cost = tot_delay + tot_wasted + tot_switch + tot_unserved
        cost_breakdown = PlanCost(
            total_cost=round(total_cost, 2),
            delay_harm_cost=round(tot_delay, 2),
            wasted_dispatch_cost=round(tot_wasted, 2),
            switching_penalty_cost=round(tot_switch, 2),
            unserved_penalty_cost=round(tot_unserved, 2),
        )

        # Compute runner-up per incident for counterfactual "why not" explanation
        runner_ups: Dict[str, RunnerUp] = {}
        for inc in incidents:
            assigned_u = next((a.unit_id for a in assignments if a.incident_id == inc.id), None)
            candidates = []
            for u in assignable_units:
                if u.id == assigned_u:
                    continue
                if (u.id, inc.id) in total_assign_costs:
                    candidates.append((u.id, total_assign_costs[(u.id, inc.id)], travel_time_matrix[(u.id, inc.id)]))

            candidates.sort(key=lambda item: item[1])
            if candidates:
                runner_id, runner_cost, runner_eta = candidates[0]
                primary_cost = total_assign_costs.get((assigned_u, inc.id), 0.0) if assigned_u else unserved_costs[inc.id]
                primary_eta = travel_time_matrix.get((assigned_u, inc.id), 0.0) if assigned_u else 0.0
                runner_ups[inc.id] = RunnerUp(
                    incident_id=inc.id,
                    unit_id=runner_id,
                    delta_eta_minutes=round(runner_eta - primary_eta, 1),
                    delta_cost=round(runner_cost - primary_cost, 2),
                    reason_not_chosen=f"Higher ETA by {round(runner_eta - primary_eta, 1)}m (cost increase: +{round(runner_cost - primary_cost, 2):.1f})"
                )
            else:
                runner_ups[inc.id] = RunnerUp(
                    incident_id=inc.id,
                    unit_id=None,
                    reason_not_chosen="No alternative reachable unit of matching type"
                )

        return Plan(
            assignments=assignments,
            unserved_incidents=unserved_list,
            cost_breakdown=cost_breakdown,
            runner_up_per_incident=runner_ups,
            status="PROPOSED"
        )

    def diff_plans(self, old_plan: Optional[Plan], new_plan: Plan) -> PlanDiff:
        """Calculate granular operational delta between two plans."""
        if old_plan is None:
            changes = [
                PlanChange(
                    unit_id=a.unit_id,
                    from_incident_id=None,
                    to_incident_id=a.incident_id,
                    reason="Initial emergency dispatch formulation",
                    cost_delta=a.cost,
                    requires_human_decision=a.requires_human_confirmation
                )
                for a in new_plan.assignments
            ]
            return PlanDiff(
                old_plan_id=None,
                new_plan_id=new_plan.plan_id,
                changes=changes,
                total_cost_delta=new_plan.cost_breakdown.total_cost,
                units_redirected=0,
                requires_human_decision=any(c.requires_human_decision for c in changes),
                summary="Initial dispatch plan formulated"
            )

        old_map = {a.unit_id: a.incident_id for a in old_plan.assignments}
        new_map = {a.unit_id: a.incident_id for a in new_plan.assignments}
        old_eta = {a.unit_id: a.eta_minutes for a in old_plan.assignments}
        new_eta = {a.unit_id: a.eta_minutes for a in new_plan.assignments}
        old_inc_eta = {a.incident_id: a.eta_minutes for a in old_plan.assignments}
        new_inc_eta = {a.incident_id: a.eta_minutes for a in new_plan.assignments}
        all_units = sorted(list(set(old_map.keys()) | set(new_map.keys())))

        changes: List[PlanChange] = []
        redirected_count = 0
        requires_decision = False

        for u_id in all_units:
            old_inc = old_map.get(u_id)
            new_inc = new_map.get(u_id)

            if old_inc != new_inc:
                if old_inc is not None and new_inc is not None:
                    kind = ChangeKind.OPTIMIZATION_REDIRECT
                    reason = f"Unit {u_id} pulled from incident {old_inc} and redirected to {new_inc}"
                    redirected_count += 1
                    req_human = True  # High risk: abandoning active assignment
                elif old_inc is None and new_inc is not None:
                    kind = ChangeKind.NEW_ASSIGNMENT
                    reason = f"Unit {u_id} newly assigned to {new_inc}"
                    req_human = False
                else:
                    kind = ChangeKind.FORCED_UNIT_LOSS
                    # Real risk check: Did the orphaned incident get worse or unserved?
                    replacement_eta = new_inc_eta.get(old_inc)
                    orig_eta = old_inc_eta.get(old_inc, 0.0)
                    if replacement_eta is None:
                        reason = f"Unit {u_id} lost (incident {old_inc} left unserved!)"
                        req_human = True
                    elif replacement_eta > orig_eta:
                        reason = f"Unit {u_id} lost: incident {old_inc} reassigned with degraded ETA ({orig_eta:.1f}m -> {replacement_eta:.1f}m)"
                        req_human = True
                    else:
                        reason = f"Unit {u_id} unavailable: incident {old_inc} covered by replacement"
                        req_human = False

                changes.append(PlanChange(
                    unit_id=u_id,
                    from_incident_id=old_inc,
                    to_incident_id=new_inc,
                    reason=reason,
                    cost_delta=0.0,
                    change_kind=kind,
                    eta_before=old_eta.get(u_id),
                    eta_after=new_eta.get(u_id),
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
# Alias for backwards compatibility with earlier engine tests
SolverConfig = AllocationConfig

AllocationEngine.solve_plan = AllocationEngine.solve






