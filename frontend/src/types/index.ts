import { components } from "./api";

// Re-export OpenAPI Schemas
export type Role = components["schemas"]["Role"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type PlanApproveRequest = components["schemas"]["PlanApproveRequest"];
export type PlanRejectRequest = components["schemas"]["PlanRejectRequest"];
export type ReportIngestRequest = components["schemas"]["ReportIngestRequest"];
export type ReportIngestResponse = components["schemas"]["ReportIngestResponse"];
export type SensorIngestRequest = components["schemas"]["SensorIngestRequest"];
export type AttackResponse = components["schemas"]["AttackResponse"];

export interface WSEvent {
  id: string;
  type: string;
  timestamp: number;
  trace_id: string;
  payload: Record<string, any>;
}

// Strongly-typed Domain Models
export type VerificationLabel = "UNVERIFIED" | "CONFIRMED" | "CONFLICTING";
export type UnitType = "ambulance" | "rescue_team" | "shelter";
export type UnitStatus = "idle" | "en_route" | "unavailable";

export interface IncidentRecord {
  id: string;
  title: string;
  description?: string;
  lat: number;
  lon: number;
  severity: number; // 1 to 5
  people_affected: number;
  required_unit_type: UnitType;
  is_life_threatening: boolean;
  reported_at: string;
  confidence: number;
  verification_label: VerificationLabel;
  credibility_score: number;
  ambiguous_fields?: string[];
}

export interface Unit {
  id: string;
  type: UnitType;
  status: UnitStatus;
  lat: number;
  lon: number;
  capacity: number;
  assigned_incident_id?: string | null;
  current_target_id?: string | null;
}

export interface Hospital {
  id: string;
  name: string;
  lat: number;
  lon: number;
  capacity: number;
  occupied: number;
}

export interface Assignment {
  unit_id: string;
  incident_id: string;
  eta_minutes?: number;
  estimated_eta_minutes?: number;
  is_provisional?: boolean;
}

export interface RunnerUpInfo {
  unit_id?: string | null;
  reason_not_chosen: string;
  cost_delta: number;
}

export interface CostBreakdown {
  total_cost?: number;
  delay_harm_cost?: number;
  wasted_dispatch_cost?: number;
  switching_penalty_cost?: number;
  unserved_penalty_cost?: number;
  delay_harm?: number;
  wasted_cost?: number;
  churn_penalty?: number;
}

export interface Plan {
  plan_id: string;
  timestamp: number;
  assignments: Assignment[];
  unserved_incidents: string[];
  cost_breakdown: CostBreakdown;
  runner_up_per_incident: Record<string, RunnerUpInfo>;
  status?: string;
}

export interface UnitDiff {
  unit_id: string;
  old_incident_id?: string | null;
  new_incident_id?: string | null;
  reason: string;
  requires_human_decision: boolean;
}

export interface PlanDiff {
  old_plan_id?: string | null;
  new_plan_id: string;
  units_redirected: number;
  reassigned_units: string[];
  total_cost_delta: number;
  requires_human_decision: boolean;
  unit_diffs: UnitDiff[];
  summary: string;
}

export interface ImpactReport {
  timestamp: number;
  flooded_roads: [string, string][];
  isolated_incidents: string[];
  average_delay_increase_pct: number;
  hospital_reachability: Record<string, boolean>;
}

export interface SecurityEvent {
  event_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  timestamp: number;
  agent_name: string;
  description: string;
  mitigation_applied?: boolean;
}

export interface AgentMessage {
  sender: string;
  receiver: string;
  type: string;
  payload: Record<string, any>;
  trace_id: string;
  timestamp: number;
}

export interface CommanderBriefing {
  plan_id: string;
  recommendation: string;
  diff_explanation: string;
  counterfactuals: Record<string, string>;
  requires_human_decision: boolean;
}

export interface StateSnapshot {
  incidents: Record<string, IncidentRecord>;
  units: Unit[];
  hospitals: Hospital[];
  verification_labels: Record<string, VerificationLabel>;
  impact_report?: ImpactReport | null;
  current_plan?: Plan | null;
  previous_approved_plan?: Plan | null;
  plan_diff?: PlanDiff | null;
  commander_briefing?: CommanderBriefing | null;
  pending_approvals?: any[];
  message_log?: AgentMessage[];
  negotiation_history?: any[];
  active_agents?: string[];
  status: string;
  veto_count: number;
  step_budget: number;
}
