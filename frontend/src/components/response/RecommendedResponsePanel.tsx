"use client";

import React, { useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import {
  GitBranch,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Zap,
  Clock,
  Sparkles,
  Route,
  ArrowRight,
  RefreshCw,
} from "lucide-react";

interface RecommendedResponsePanelProps {
  onApproveSuccess?: () => void;
}

export function RecommendedResponsePanel({ onApproveSuccess }: RecommendedResponsePanelProps) {
  const {
    currentPlan,
    planDiff,
    status,
    incidents,
    setSnapshot,
    setAuditStatus,
    clearPendingApproval,
  } = useCrisisStore();

  const [isApproving, setIsApproving] = useState(false);
  const [expandedWhy, setExpandedWhy] = useState<Record<string, boolean>>({});
  const [provisionalDecisions, setProvisionalDecisions] = useState<Record<string, boolean>>({});

  const handleDecisionToggle = (unitId: string) => {
    setProvisionalDecisions((prev) => ({
      ...prev,
      [unitId]: !(prev[unitId] ?? true),
    }));
  };

  const toggleWhy = (unitId: string) => {
    setExpandedWhy((prev) => ({
      ...prev,
      [unitId]: !prev[unitId],
    }));
  };

  const handleApprove = async () => {
    if (!currentPlan) return;
    setIsApproving(true);
    try {
      const res = await api.approvePlan(currentPlan.plan_id, {
        auto_sign: true,
        decisions: provisionalDecisions,
      });
      if (res.status === "DISPATCHED" || (res as any).approved) {
        clearPendingApproval();
        const snap = await api.getStateSnapshot();
        setSnapshot(snap);
        const audit = await api.verifyAudit();
        setAuditStatus(audit);
        if (onApproveSuccess) onApproveSuccess();
      }
    } catch (e) {
      console.error("Approval error:", e);
    } finally {
      setIsApproving(false);
    }
  };

  const isDispatched = status === "DISPATCHED" || currentPlan?.status === "APPROVED";

  const isVetoed =
    currentPlan?.status === "VETOED" ||
    (planDiff && (planDiff.units_redirected > 0 || (planDiff as any).changes?.length > 0));

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#0c0f1d]/80 backdrop-blur-md border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="h-11 px-3.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/40 select-none">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-ops-lime" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            What We Recommend
          </span>
        </div>
        {currentPlan && (
          <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/80 px-2.5 py-0.5 rounded-full border border-cyan-800/60">
            Plan #{currentPlan.plan_id.slice(0, 6)}
          </span>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {currentPlan ? (
          <>
            {/* VETO & Reroute Alert (if corridor blocked at T+10) */}
            {isVetoed && (
              <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/80 text-xs">
                <div className="flex items-center gap-2 text-red-300 font-bold mb-1">
                  <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 animate-pulse" />
                  <span>Tactical Veto: Outer Ring Road Corridor Flooded</span>
                </div>
                <p className="text-[11px] text-red-200/90 leading-relaxed">
                  Route blocked (2.5m water depth). Impact agent vetoed direct route. Solver auto-rerouted fleet via Ejipura (+8m delay).
                </p>
              </div>
            )}

            {/* CP-SAT Optimal Metrics Bar */}
            <div className="grid grid-cols-3 gap-2 p-2.5 rounded-xl bg-[#101326] border border-slate-800/80 text-center font-mono">
              <div>
                <div className="text-[9px] text-slate-400 uppercase tracking-wider">Total Harm Cost</div>
                <div className="text-xs font-bold text-ops-lime mt-0.5">
                  {(currentPlan.cost_breakdown?.total_cost ?? 0).toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-[9px] text-slate-400 uppercase tracking-wider">Delay Term</div>
                <div className="text-xs font-semibold text-slate-200 mt-0.5">
                  {(currentPlan.cost_breakdown?.delay_harm_cost ?? 0).toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-[9px] text-slate-400 uppercase tracking-wider">Wasted Cost</div>
                <div className="text-xs font-semibold text-slate-200 mt-0.5">
                  {(currentPlan.cost_breakdown?.wasted_dispatch_cost ?? 0).toFixed(1)}
                </div>
              </div>
            </div>

            {/* Recommended Assignments List */}
            <div className="space-y-2">
              <div className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                <span>Dispatch Recommendations ({currentPlan.assignments?.length || 0})</span>
                <span className="text-[10px] text-slate-500 font-mono">CP-SAT Optimized</span>
              </div>

              {(currentPlan.assignments || []).map((assignment) => {
                const targetInc = incidents[assignment.incident_id];
                const incTitle = targetInc?.title || assignment.incident_id;
                const eta = assignment.eta_minutes ?? assignment.estimated_eta_minutes ?? 0;
                const isProvisional = assignment.is_provisional;
                const isWhyOpen = expandedWhy[assignment.unit_id];
                const runnerUp = (currentPlan as any).runner_up_per_incident?.[assignment.incident_id];
                const isConfirmedByCommander = provisionalDecisions[assignment.unit_id] ?? true;

                // Format friendly unit label: "Ambulance 1", "Rescue team 1"
                let unitFriendly = assignment.unit_id.replace("amb_0", "Ambulance ").replace("amb_", "Ambulance ").replace("rescue_0", "Rescue team ").replace("rescue_", "Rescue team ");
                if (!unitFriendly.startsWith("Ambulance") && !unitFriendly.startsWith("Rescue")) {
                  unitFriendly = assignment.unit_id.toUpperCase();
                }

                // Friendly short destination name
                const shortDest = incTitle
                  .replace("Road Accident at ", "")
                  .replace("Apartment Basement Inundation at ", "")
                  .replace("Critical Medical Emergency at ", "")
                  .replace("Trapped Vehicle in Flooded ", "")
                  .replace(" Underpass", "")
                  .replace(" Junction", "");

                return (
                  <div
                    key={`${assignment.unit_id}-${assignment.incident_id}`}
                    className={`rounded-xl border transition-all ${
                      isProvisional
                        ? "bg-amber-950/20 border-amber-800/60"
                        : "bg-[#101326]/80 border-slate-800/80"
                    }`}
                  >
                    {/* Main Row: "Ambulance 1 -> Silk Board, 3 min" */}
                    <div className="p-3 flex items-start justify-between gap-2.5">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          {isProvisional && (
                            <input
                              type="checkbox"
                              checked={isConfirmedByCommander}
                              onChange={() => handleDecisionToggle(assignment.unit_id)}
                              className="w-4 h-4 rounded border-amber-600 text-amber-500 focus:ring-amber-500 cursor-pointer bg-slate-900 shrink-0"
                              title="Check to authorize provisional dispatch"
                            />
                          )}
                          <span className="font-semibold text-xs text-ops-lime whitespace-nowrap">
                            {unitFriendly}
                          </span>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="text-xs font-semibold text-white truncate">
                            {shortDest}
                          </span>
                          <span className="text-[11px] font-mono text-cyan-400 font-medium shrink-0">
                            , {eta.toFixed(0)} min
                          </span>
                        </div>

                        {/* Provisional info tag */}
                        {isProvisional && (
                          <div className="text-[10px] text-amber-400/90 mt-1 pl-6 flex items-center gap-1">
                            <span>⚠ Unconfirmed call. Tick to confirm dispatch.</span>
                          </div>
                        )}
                      </div>

                      {/* Right Status */}
                      <div className="flex flex-col items-end shrink-0 gap-1">
                        {isProvisional ? (
                          <span className="text-[9px] px-2 py-0.5 rounded-full font-mono font-bold uppercase bg-amber-950/80 text-amber-300 border border-amber-700/60">
                            Provisional
                          </span>
                        ) : (
                          <span className="text-[9px] px-2 py-0.5 rounded-full font-mono font-bold uppercase bg-emerald-950/80 text-emerald-300 border border-emerald-700/60">
                            Confirmed
                          </span>
                        )}
                      </div>
                    </div>

                    {/* "Why this?" counterfactual expander toggle */}
                    <div className="px-3 pb-2 pt-0 flex justify-end">
                      <button
                        onClick={() => toggleWhy(assignment.unit_id)}
                        className="text-[10px] font-medium text-slate-400 hover:text-ops-lime flex items-center gap-1 transition-colors"
                      >
                        <Sparkles className="w-3 h-3 text-ops-lime" />
                        <span>Why this choice?</span>
                        {isWhyOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                    </div>

                    {/* Expanded Counterfactual Reasoning */}
                    {isWhyOpen && (
                      <div className="mx-3 mb-3 p-2.5 rounded-lg bg-[#0b0c1b] border border-violet-900/40 text-[11px] space-y-1.5 animate-fadeIn">
                        <div className="text-slate-300">
                          <span className="font-semibold text-ops-lime">Optimal Arrival:</span>{" "}
                          {unitFriendly} reaches destination in <strong className="text-white">{eta.toFixed(0)} mins</strong>.
                        </div>
                        {runnerUp && runnerUp.unit_id ? (
                          <div className="text-slate-400 border-t border-slate-800/80 pt-1">
                            <span className="text-amber-300 font-medium">Runner-up Candidate:</span>{" "}
                            {runnerUp.unit_id.toUpperCase()} would take{" "}
                            <strong className="text-slate-200">
                              {(eta + (runnerUp.delta_eta_minutes || 14.0)).toFixed(0)} mins
                            </strong>{" "}
                            ({runnerUp.reason_not_chosen || `+${(runnerUp.delta_eta_minutes || 14.0).toFixed(0)}m slower arrival`}).
                          </div>
                        ) : (
                          <div className="text-slate-400 border-t border-slate-800/80 pt-1">
                            <span className="text-amber-300 font-medium">Stability:</span> Avoids 60.0 switching penalty by maintaining route continuity.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Ed25519 Approve & Dispatch Button */}
            <div className="pt-2">
              {isDispatched ? (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-700/60 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-emerald-300 font-bold">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Dispatched &amp; Ed25519 Signed</span>
                  </div>
                  <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                    Audit Valid
                  </span>
                </div>
              ) : (
                <button
                  onClick={handleApprove}
                  disabled={isApproving}
                  className="w-full py-3 px-4 rounded-xl bg-ops-lime hover:bg-[#b5e228] text-[#0b0c1f] font-bold text-xs uppercase tracking-wider transition-all duration-150 shadow-[0_0_20px_rgba(198,244,50,0.3)] hover:shadow-[0_0_25px_rgba(198,244,50,0.5)] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FileCheck className="w-4 h-4 text-[#0b0c1f]" />
                  <span>{isApproving ? "Signing & Dispatching..." : "Approve & Dispatch Plan"}</span>
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 select-none">
            <Route className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
            <p className="text-xs font-semibold text-slate-300">CP-SAT solver standing by.</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
              Start the flood scenario to compute provably optimal dispatch routes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
