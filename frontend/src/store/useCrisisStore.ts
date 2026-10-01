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
  AttackResponse,
  USPProofResponse,
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

  connectionStatus: ConnectionStatus;
  scenarioClock: string;
  lastEventId: string | null;
  isOfflineMap: boolean;
  selectedIncidentId: string | null;
  selectedUnitId: string | null;
  pendingApproval: PendingApproval | null;
  vetoCount: number;

  // Phase 7 Demo & Presenter State
  isPresenterMode: boolean;
  isSafeMode: boolean;
  isAttackPanelOpen: boolean;
  isUSPPanelOpen: boolean;
  playbackSpeed: number;
  isPlaying: boolean;
  lastAttackOutcome: AttackResponse | null;
  highlightedTraceId: string | null;
  uspProofData: USPProofResponse | null;
  isUnderTheHood: boolean;

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

  // Phase 7 Actions
  togglePresenterMode: () => void;
  setPresenterMode: (val: boolean) => void;
  toggleSafeMode: () => void;
  setSafeMode: (val: boolean) => void;
  toggleAttackPanel: () => void;
  setAttackPanelOpen: (val: boolean) => void;
  toggleUSPPanel: () => void;
  setUSPPanelOpen: (val: boolean) => void;
  setPlaybackSpeed: (speed: number) => void;
  setIsPlaying: (val: boolean) => void;
  setLastAttackOutcome: (outcome: AttackResponse | null) => void;
  setHighlightedTraceId: (id: string | null) => void;
  setUSPProofData: (data: USPProofResponse | null) => void;
  toggleUnderTheHood: () => void;
  setIsUnderTheHood: (val: boolean) => void;
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
  scenarioClock: "T+00:00",
  lastEventId: null,
  isOfflineMap: true,
  selectedIncidentId: null,
  selectedUnitId: null,
  pendingApproval: null,
  vetoCount: 0,

  // Phase 7 Initial State
  isPresenterMode: true, // Default to true for rich presenter capabilities
  isSafeMode: true,      // Default to true for safe local demo execution
  isAttackPanelOpen: false,
  isUSPPanelOpen: false,
  playbackSpeed: 1.0,
  isPlaying: false,
  lastAttackOutcome: null,
  highlightedTraceId: null,
  uspProofData: null,

  setSnapshot: (snapshot: StateSnapshot) =>
    set((state) => {
      // Restore pending approval if state indicates waiting or approvals exist
      let pendingApproval: PendingApproval | null = null;
      if (snapshot.pending_approvals && snapshot.pending_approvals.length > 0) {
        const p = snapshot.pending_approvals[0];
        pendingApproval = {
          plan_id: p.plan_id,
          plan_hash: p.plan_hash,
          briefing: snapshot.commander_briefing || null,
        };
      } else if (snapshot.status === "AWAITING_COMMANDER_APPROVAL" && snapshot.current_plan) {
        pendingApproval = {
          plan_id: snapshot.current_plan.plan_id,
          plan_hash: (snapshot.current_plan as any).plan_hash || "",
          briefing: snapshot.commander_briefing || null,
        };
      }

      // Format agent trace from message_log
      const agentTrace: AgentMessage[] = (snapshot.message_log || []).map((m: any) => ({
        sender: m.sender || "Agent",
        receiver: m.receiver || "Broadcast",
        type: m.type || "Update",
        payload: m.payload || {},
        trace_id: m.trace_id || "",
        timestamp: m.timestamp || Date.now() / 1000,
      })).slice(-150).reverse();

      // Hydrate scenario clock
      let scenarioClock = state.scenarioClock;
      if (snapshot.incidents && snapshot.incidents["inc_t10_critical_underpass"]) {
        scenarioClock = "T+10:00";
      } else if (snapshot.status === "RUNNING_T0" || snapshot.status === "AWAITING_COMMANDER_APPROVAL" || snapshot.status === "INITIALIZED") {
        scenarioClock = "T+00:00";
      }

      return {
        incidents: snapshot.incidents || {},
        units: snapshot.units || [],
        hospitals: snapshot.hospitals || [],
        currentPlan: snapshot.current_plan || null,
        previousApprovedPlan: snapshot.previous_approved_plan || null,
        planDiff: snapshot.plan_diff || null,
        impactReport: snapshot.impact_report || null,
        commanderBriefing: snapshot.commander_briefing || null,
        status: snapshot.status || "INITIALIZED",
        pendingApproval,
        vetoCount: snapshot.veto_count || 0,
        agentTrace: agentTrace.length > 0 ? agentTrace : state.agentTrace,
        scenarioClock,
      };
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
          if (payload.action === "reset" || payload.action === "start") {
            updates.scenarioClock = "T+00:00";
          } else if (payload.action === "step") {
            updates.scenarioClock = "T+10:00";
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

  // Phase 7 Actions
  togglePresenterMode: () => set((state) => ({ isPresenterMode: !state.isPresenterMode })),
  setPresenterMode: (isPresenterMode: boolean) => set({ isPresenterMode }),
  toggleSafeMode: () => set((state) => ({ isSafeMode: !state.isSafeMode, isOfflineMap: !state.isSafeMode })),
  setSafeMode: (isSafeMode: boolean) => set({ isSafeMode, isOfflineMap: isSafeMode }),
  toggleAttackPanel: () => set((state) => ({ isAttackPanelOpen: !state.isAttackPanelOpen })),
  setAttackPanelOpen: (isAttackPanelOpen: boolean) => set({ isAttackPanelOpen }),
  toggleUSPPanel: () => set((state) => ({ isUSPPanelOpen: !state.isUSPPanelOpen })),
  setUSPPanelOpen: (isUSPPanelOpen: boolean) => set({ isUSPPanelOpen }),
  setPlaybackSpeed: (playbackSpeed: number) => set({ playbackSpeed }),
  setIsPlaying: (isPlaying: boolean) => set({ isPlaying }),
  setLastAttackOutcome: (lastAttackOutcome: AttackResponse | null) => set({ lastAttackOutcome }),
  setHighlightedTraceId: (highlightedTraceId: string | null) => set({ highlightedTraceId }),
  setUSPProofData: (uspProofData: USPProofResponse | null) => set({ uspProofData }),
  isUnderTheHood: false,
  toggleUnderTheHood: () => set((state) => ({ isUnderTheHood: !state.isUnderTheHood })),
  setIsUnderTheHood: (isUnderTheHood: boolean) => set({ isUnderTheHood }),
}));
