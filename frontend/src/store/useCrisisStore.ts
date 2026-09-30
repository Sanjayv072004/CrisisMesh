import { create } from "zustand";
import {
  IncidentRecord,
  Unit,
  Hospital,
  Plan,
  PlanDiff,
  ImpactReport,
  CommanderBriefing,
  SecurityEvent,
  AgentMessage,
  StateSnapshot,
  Role,
  WSEvent,
} from "@/types";

export type ConnectionStatus = "CONNECTED" | "CONNECTING" | "DISCONNECTED" | "ERROR";

export interface PendingApproval {
  plan_id: string;
  plan_hash: string;
  briefing?: CommanderBriefing | null;
  rejection_reason?: string;
}

interface CrisisState {
  // Operational Data
  incidents: Record<string, IncidentRecord>;
  units: Unit[];
  hospitals: Hospital[];
  currentPlan: Plan | null;
  previousApprovedPlan: Plan | null;
  planDiff: PlanDiff | null;
  impactReport: ImpactReport | null;
  commanderBriefing: CommanderBriefing | null;
  status: string;

  // Security & Audit
  securityEvents: SecurityEvent[];
  auditStatus: {
    is_valid: boolean;
    total_entries: number;
    status: string;
  };

  // Agent Trace
  agentTrace: AgentMessage[];

  // User & Roles
  activeRole: Role;
  userId: string;

  // System & Connection
  connectionStatus: ConnectionStatus;
  lastEventId: string | null;
  isOfflineMap: boolean;
  selectedIncidentId: string | null;
  selectedUnitId: string | null;
  pendingApproval: PendingApproval | null;

  // Actions
  setSnapshot: (snapshot: StateSnapshot) => void;
  handleWsEvent: (event: WSEvent) => void;
  setActiveRole: (role: Role) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setLastEventId: (id: string | null) => void;
  setSelectedIncident: (id: string | null) => void;
  setSelectedUnit: (id: string | null) => void;
  toggleOfflineMap: () => void;
  clearPendingApproval: () => void;
  setAuditStatus: (status: { is_valid: boolean; total_entries: number; status: string }) => void;
}

export const useCrisisStore = create<CrisisState>((set) => ({
  incidents: {},
  units: [],
  hospitals: [],
  currentPlan: null,
  previousApprovedPlan: null,
  planDiff: null,
  impactReport: null,
  commanderBriefing: null,
  status: "INITIALIZED",

  securityEvents: [],
  auditStatus: {
    is_valid: true,
    total_entries: 0,
    status: "VERIFIED",
  },

  agentTrace: [],
  activeRole: "commander",
  userId: "commander",

  connectionStatus: "DISCONNECTED",
  lastEventId: null,
  isOfflineMap: false,
  selectedIncidentId: null,
  selectedUnitId: null,
  pendingApproval: null,

  setSnapshot: (snapshot: StateSnapshot) =>
    set({
      incidents: snapshot.incidents || {},
      units: snapshot.units || [],
      hospitals: snapshot.hospitals || [],
      currentPlan: snapshot.current_plan || null,
      previousApprovedPlan: snapshot.previous_approved_plan || null,
      planDiff: snapshot.plan_diff || null,
      impactReport: snapshot.impact_report || null,
      commanderBriefing: snapshot.commander_briefing || null,
      status: snapshot.status || "INITIALIZED",
      agentTrace: snapshot.message_log || [],
    }),

  handleWsEvent: (event: WSEvent) => {
    set((state) => {
      const updates: Partial<CrisisState> = {
        lastEventId: event.id || state.lastEventId,
      };

      const payload = event.payload || {};

      switch (event.type) {
        case "agent_message": {
          const msg: AgentMessage = {
            sender: payload.sender || "Agent",
            receiver: payload.receiver || "Broadcast",
            type: payload.type || "Update",
            payload: payload.payload || {},
            trace_id: event.trace_id || "",
            timestamp: event.timestamp || Date.now() / 1000,
          };
          // Limit agent trace buffer to latest 150 messages
          updates.agentTrace = [msg, ...state.agentTrace].slice(0, 150);
          break;
        }

        case "incident_updated": {
          if (payload.incidents) {
            updates.incidents = { ...state.incidents, ...payload.incidents };
          }
          break;
        }

        case "impact_updated": {
          updates.impactReport = payload as ImpactReport;
          break;
        }

        case "plan_proposed": {
          updates.currentPlan = payload as Plan;
          break;
        }

        case "plan_diff": {
          updates.planDiff = payload as PlanDiff;
          break;
        }

        case "approval_required": {
          updates.status = "AWAITING_COMMANDER_APPROVAL";
          updates.pendingApproval = {
            plan_id: payload.plan_id,
            plan_hash: payload.plan_hash,
            briefing: payload.briefing,
            rejection_reason: payload.rejection_reason,
          };
          if (payload.briefing) {
            updates.commanderBriefing = payload.briefing;
          }
          break;
        }

        case "plan_approved": {
          updates.status = "DISPATCHED";
          updates.pendingApproval = null;
          break;
        }

        case "dispatch_issued": {
          updates.status = "DISPATCHED";
          break;
        }

        case "security_event": {
          const secEvt = payload as SecurityEvent;
          updates.securityEvents = [secEvt, ...state.securityEvents].slice(0, 50);
          break;
        }

        case "audit_status": {
          updates.auditStatus = {
            is_valid: payload.is_valid ?? true,
            total_entries: payload.total_entries ?? state.auditStatus.total_entries,
            status: payload.status ?? "VERIFIED",
          };
          break;
        }

        case "scenario_status": {
          if (payload.status) {
            updates.status = payload.status;
          }
          break;
        }

        default:
          break;
      }

      return updates;
    });
  },

  setActiveRole: (role: Role) => set({ activeRole: role, userId: role }),
  setConnectionStatus: (connectionStatus: ConnectionStatus) => set({ connectionStatus }),
  setLastEventId: (lastEventId: string | null) => set({ lastEventId }),
  setSelectedIncident: (selectedIncidentId: string | null) => set({ selectedIncidentId }),
  setSelectedUnit: (selectedUnitId: string | null) => set({ selectedUnitId }),
  toggleOfflineMap: () => set((state) => ({ isOfflineMap: !state.isOfflineMap })),
  clearPendingApproval: () => set({ pendingApproval: null }),
  setAuditStatus: (auditStatus) => set({ auditStatus }),
}));
