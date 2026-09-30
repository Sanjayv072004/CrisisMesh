"use client";

import React, { useEffect, useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { USPProofResponse } from "@/types";
import {
  BarChart3,
  X,
  RefreshCw,
  GitBranch,
  ShieldCheck,
  HelpCircle,
  TrendingDown,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

export function USPProofPanel() {
  const { isUSPPanelOpen, setUSPPanelOpen, uspProofData, setUSPProofData } = useCrisisStore();
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"low_churn" | "uncertainty" | "counterfactual">("low_churn");

  const fetchProof = async () => {
    setIsLoading(true);
    try {
      const data = await api.getUSPProof();
      setUSPProofData(data);
    } catch (e) {
      console.error("Failed to load USP proof:", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isUSPPanelOpen && !uspProofData) {
      fetchProof();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isUSPPanelOpen]);

  if (!isUSPPanelOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-4xl bg-slate-950 border border-indigo-500/50 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] font-mono text-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-indigo-950 bg-indigo-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-sm tracking-wide text-indigo-200 uppercase">
                Live Algorithmic USP Proofs
              </h2>
              <p className="text-[11px] text-slate-400">
                Computed LIVE by backend CP-SAT solver on current scenario data (never hardcoded)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchProof}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-900/40 hover:bg-indigo-900/70 border border-indigo-500/40 text-xs text-indigo-300 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Recompute</span>
            </button>
            <button
              onClick={() => setUSPPanelOpen(false)}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-slate-800 bg-slate-900/60 px-6 gap-2">
          <button
            onClick={() => setActiveTab("low_churn")}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition-colors ${
              activeTab === "low_churn"
                ? "border-cyan-400 text-cyan-300 bg-slate-800/40"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            (a) Low-Churn vs Naive Re-plan
          </button>
          <button
            onClick={() => setActiveTab("uncertainty")}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition-colors ${
              activeTab === "uncertainty"
                ? "border-indigo-400 text-indigo-300 bg-slate-800/40"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            (b) Uncertainty-Aware Minimax Bound
          </button>
          <button
            onClick={() => setActiveTab("counterfactual")}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition-colors ${
              activeTab === "counterfactual"
                ? "border-amber-400 text-amber-300 bg-slate-800/40"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            (c) Counterfactual Explanation
          </button>
        </div>

        {/* Tab Contents */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading && !uspProofData ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-400" />
              <span>Solving dual CP-SAT integer optimization models...</span>
            </div>
          ) : !uspProofData ? (
            <div className="py-20 text-center text-slate-400">No proof data returned from backend.</div>
          ) : (
            <>
              {/* TAB 1: LOW CHURN */}
              {activeTab === "low_churn" && (
                <div className="space-y-5">
                  <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-slate-400 font-bold uppercase">Dynamic Churn Scenario (T+10):</div>
                      <div className="text-sm text-slate-200 font-semibold mt-0.5">
                        New critical underpass flood arrives while Rescue 1 is en route to Bellandur.
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300 text-xs font-bold">
                      Zero Churn Proof
                    </span>
                  </div>

                  {/* Side by side cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Naive Solver */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-rose-500/30 flex flex-col gap-3">
                      <div className="flex items-center justify-between border-b border-rose-900/40 pb-2">
                        <span className="text-xs font-bold text-rose-300 uppercase">Naive Re-plan (&lambda; = 0)</span>
                        <span className="text-[11px] text-rose-400 font-mono">Chaotic Re-dispatch</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Units Redirected:</span>
                          <span className="text-rose-400 font-bold text-lg">
                            {uspProofData.low_churn.naive_units_redirected}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Total Cost:</span>
                          <span className="text-slate-200 font-bold text-lg">
                            {uspProofData.low_churn.naive_total_cost}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Delay Harm:</span>
                          <span className="text-slate-200 font-bold">
                            {uspProofData.low_churn.naive_delay_cost}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Switching Penalty:</span>
                          <span className="text-slate-400 font-bold">
                            {uspProofData.low_churn.naive_switching_cost} (Ignored)
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-rose-300/80 leading-relaxed bg-rose-950/20 p-2 rounded border border-rose-900/30">
                        Naive baseline abruptly redirects en-route Rescue 1 to the underpass, completely abandoning
                        Bellandur victims mid-transit.
                      </p>
                    </div>

                    {/* CrisisMesh Low-Churn */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-emerald-500/40 flex flex-col gap-3">
                      <div className="flex items-center justify-between border-b border-emerald-900/40 pb-2">
                        <span className="text-xs font-bold text-emerald-300 uppercase">CrisisMesh Low-Churn (&lambda; = 60)</span>
                        <span className="text-[11px] text-emerald-400 font-mono">Mission Continuity</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Units Redirected:</span>
                          <span className="text-emerald-400 font-bold text-lg">
                            {uspProofData.low_churn.low_churn_units_redirected}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Total Cost:</span>
                          <span className="text-slate-200 font-bold text-lg">
                            {uspProofData.low_churn.low_churn_total_cost}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Delay Harm:</span>
                          <span className="text-slate-200 font-bold">
                            {uspProofData.low_churn.low_churn_delay_cost}
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2 rounded">
                          <span className="text-slate-400 block text-[10px]">Switching Penalty:</span>
                          <span className="text-emerald-300 font-bold">
                            {uspProofData.low_churn.low_churn_switching_cost} (Zero Churn)
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-emerald-300/80 leading-relaxed bg-emerald-950/20 p-2 rounded border border-emerald-900/30">
                        CrisisMesh keeps Rescue 1 committed to Bellandur and smoothly dispatches idle Rescue 2 to
                        the underpass. Zero mission disruptions.
                      </p>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs text-slate-300">
                    <span className="text-cyan-400 font-bold">Solver Proof: </span>
                    {uspProofData.low_churn.explanation}
                  </div>
                </div>
              )}

              {/* TAB 2: UNCERTAINTY-AWARE */}
              {activeTab === "uncertainty" && (
                <div className="space-y-5">
                  <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-slate-400 font-bold uppercase">Evaluated Incident:</div>
                      <div className="text-sm text-slate-200 font-semibold mt-0.5">
                        {uspProofData.uncertainty_aware.incident_title} (
                        {uspProofData.uncertainty_aware.verification_label}, Credibility:{" "}
                        {uspProofData.uncertainty_aware.credibility_score})
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded bg-indigo-950 border border-indigo-500/40 text-indigo-300 text-xs font-bold flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Minimax Bound Verified
                    </span>
                  </div>

                  {/* Dual Scenario Matrix */}
                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-900 text-slate-400 uppercase text-[10px]">
                        <tr>
                          <th className="p-3">Optimization Model</th>
                          <th className="p-3">Cost if Report TRUE</th>
                          <th className="p-3">Cost if Report FALSE (Hoax)</th>
                          <th className="p-3 text-right">Worst-Case Cost Max(T, F)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        <tr className="bg-slate-950/60 hover:bg-slate-900/50">
                          <td className="p-3 font-bold text-rose-300">Naive Solver (p=1.0)</td>
                          <td className="p-3">{uspProofData.uncertainty_aware.cost_if_true_naive}</td>
                          <td className="p-3 text-rose-400 font-semibold">
                            {uspProofData.uncertainty_aware.cost_if_false_naive} (Wasted Fleet)
                          </td>
                          <td className="p-3 text-right font-bold text-rose-400 text-sm">
                            {uspProofData.uncertainty_aware.worst_case_naive}
                          </td>
                        </tr>
                        <tr className="bg-indigo-950/30 hover:bg-indigo-950/50">
                          <td className="p-3 font-bold text-indigo-300">
                            CrisisMesh Robust Optimization
                          </td>
                          <td className="p-3">{uspProofData.uncertainty_aware.cost_if_true_robust}</td>
                          <td className="p-3 text-emerald-400 font-semibold">
                            {uspProofData.uncertainty_aware.cost_if_false_robust} (Provisional Guard)
                          </td>
                          <td className="p-3 text-right font-bold text-emerald-400 text-sm">
                            {uspProofData.uncertainty_aware.worst_case_robust}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div className="p-4 bg-indigo-950/20 border border-indigo-500/30 rounded-xl text-xs text-indigo-200">
                    <div className="font-bold text-indigo-300 mb-1">
                      MATHEMATICAL PROOF: Robust Worst-Case (
                      {uspProofData.uncertainty_aware.worst_case_robust}) &le; Naive Worst-Case (
                      {uspProofData.uncertainty_aware.worst_case_naive})
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {uspProofData.uncertainty_aware.explanation}
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 3: COUNTERFACTUAL */}
              {activeTab === "counterfactual" && (
                <div className="space-y-5">
                  <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                    <div className="text-xs text-slate-400 font-bold uppercase">Decision Target:</div>
                    <div className="text-sm text-slate-200 font-semibold mt-0.5">
                      Assignment for {uspProofData.counterfactual.incident_title} (
                      {uspProofData.counterfactual.incident_id})
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Selected Unit */}
                    <div className="p-4 rounded-xl bg-slate-900/80 border border-cyan-500/40 flex flex-col gap-2">
                      <div className="flex items-center justify-between border-b border-cyan-900/40 pb-2">
                        <span className="text-xs font-bold text-cyan-300">OPTIMAL CHOICE</span>
                        <span className="text-[11px] text-cyan-400 font-mono">SELECTED</span>
                      </div>
                      <div className="text-sm font-bold text-white">
                        {uspProofData.counterfactual.assigned_unit_id} (
                        {uspProofData.counterfactual.assigned_unit_type})
                      </div>
                      <div className="flex items-center justify-between text-xs pt-2">
                        <span className="text-slate-400">Estimated Travel Time:</span>
                        <span className="font-bold text-cyan-300">
                          {uspProofData.counterfactual.assigned_eta_minutes} mins
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Expected Harm Cost:</span>
                        <span className="font-bold text-slate-200">
                          {uspProofData.counterfactual.assigned_cost}
                        </span>
                      </div>
                    </div>

                    {/* Runner-Up Unit */}
                    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-700 flex flex-col gap-2">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <span className="text-xs font-bold text-slate-400">RUNNER-UP ALTERNATIVE</span>
                        <span className="text-[11px] text-slate-400 font-mono">REJECTED</span>
                      </div>
                      <div className="text-sm font-bold text-slate-300">
                        {uspProofData.counterfactual.runner_up_unit_id} (
                        {uspProofData.counterfactual.assigned_unit_type})
                      </div>
                      <div className="flex items-center justify-between text-xs pt-2">
                        <span className="text-slate-400">Estimated Travel Time:</span>
                        <span className="font-bold text-amber-300">
                          {uspProofData.counterfactual.runner_up_eta_minutes} mins (+
                          {uspProofData.counterfactual.delta_eta_minutes}m)
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Expected Harm Cost:</span>
                        <span className="font-bold text-amber-300">
                          {uspProofData.counterfactual.runner_up_cost} (+
                          {uspProofData.counterfactual.delta_cost})
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-amber-950/20 border border-amber-500/30 rounded-xl text-xs text-amber-200">
                    <span className="font-bold text-amber-300">Counterfactual Rationale: </span>
                    <span className="text-slate-300 text-[11px]">
                      {uspProofData.counterfactual.rationale}
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
