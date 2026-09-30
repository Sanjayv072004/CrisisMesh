"use client";

import React, { useState, useMemo } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/websocket";
import { TopBar } from "./TopBar";
import { PresenterControls } from "../demo/PresenterControls";
import { SafeModeBanner } from "../demo/SafeModeBanner";
import { AttackPanel } from "../demo/AttackPanel";
import { USPProofPanel } from "../demo/USPProofPanel";
import { BengaluruTacticalMap } from "../map/BengaluruTacticalMap";
import { AgentFlowView } from "../demo/AgentFlowView";
import { SecurityFeed } from "../security/SecurityFeed";
import {
  AlertTriangle,
  Ambulance,
  GitBranch,
  Terminal,
  Activity,
  Cpu,
  CheckCircle2,
  Lock,
  Radio,
  FileCheck,
  Shield,
  Layers,
  Flame,
  ShieldAlert,
  Play,
} from "lucide-react";

export function AppShell() {
  const {
    incidents,
    units,
    currentPlan,
    planDiff,
    agentTrace,
    status,
    activeRole,
    pendingApproval,
    clearPendingApproval,
    setSnapshot,
    setAuditStatus,
  } = useCrisisStore();

  const [leftTab, setLeftTab] = useState<"incidents" | "security">("incidents");
  const [rightTab, setRightTab] = useState<"plan" | "trace">("plan");
  const [isApproving, setIsApproving] = useState(false);
  const [provisionalDecisions, setProvisionalDecisions] = useState<Record<string, boolean>>({});

  // Auto-authenticate as Commander on load, connect WebSocket, and fetch state
  React.useEffect(() => {
    let isMounted = true;
    const initSession = async () => {
      try {
        const auth = await api.demoLogin("commander");
        if (!isMounted) return;
        wsClient.connect(auth.access_token);
        const snap = await api.getStateSnapshot();
        if (isMounted && snap) {
          setSnapshot(snap);
        }
        const audit = await api.verifyAudit();
        if (isMounted && audit) {
          setAuditStatus(audit);
        }
      } catch (e) {
        console.warn("Initial session hydration:", e);
      }
    };
    initSession();
    return () => {
      isMounted = false;
    };
  }, [setSnapshot, setAuditStatus]);

  // Filter out adversarial/quarantined reports from incident queue
  const incidentList = useMemo(() => {
    return Object.values(incidents).filter((inc) => {
      if (inc.credibility_score !== undefined && inc.credibility_score < 0.15) {
        return false; // Quarantined report -> shown in SecurityFeed
      }
      return true;
    });
  }, [incidents]);

  const handleDecisionToggle = (unitId: string) => {
    setProvisionalDecisions((prev) => ({
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
      if (res.status === "DISPATCHED") {
        clearPendingApproval();
        const snap = await api.getStateSnapshot();
        setSnapshot(snap);
        const audit = await api.verifyAudit();
        setAuditStatus(audit);
      }
    } catch (e) {
      console.error("Approval failed:", e);
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#070a12] text-slate-100 overflow-hidden font-sans antialiased">
      {/* 1. Header & Safe Mode Banner */}
      <TopBar />
      <SafeModeBanner />

      {/* 2. Top Banner: Multi-Agent State Flow Graph */}
      <div className="px-3 pt-2 shrink-0">
        <AgentFlowView />
      </div>

      {/* 3. Main 1080p Tactical Control Room Grid */}
      <main className="flex-1 grid grid-cols-12 gap-2 p-3 min-h-0">
        {/* Left Column (3 cols): Incidents Queue & Fleet Units / Security Feed */}
        <section aria-label="Operations Sidebar" className="col-span-3 flex flex-col gap-2 min-h-0">
          {/* Top Half: Incidents Queue / Security Feed Tabs */}
          <div className="flex-1 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl">
            {/* Header Tabs */}
            <div className="h-9 border-b border-ops-border px-2 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setLeftTab("incidents")}
                  className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1.5 transition-colors ${
                    leftTab === "incidents"
                      ? "bg-slate-800 text-white border border-slate-700"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-ops-red" />
                  <span>Incidents ({incidentList.length})</span>
                </button>
                <button
                  onClick={() => setLeftTab("security")}
                  className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1.5 transition-colors ${
                    leftTab === "security"
                      ? "bg-slate-800 text-ops-red border border-red-900/60"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5 text-ops-red" />
                  <span>Security Feed</span>
                </button>
              </div>
              <span className="text-[10px] font-mono text-ops-muted uppercase">Verified</span>
            </div>

            {leftTab === "security" ? (
              <SecurityFeed />
            ) : (
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {incidentList.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-4 text-ops-muted select-none">
                    <Activity className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
                    <p className="text-xs font-semibold text-slate-300">No active incidents reported.</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Click &apos;Start T0&apos; in header to ingest flood reports.
                    </p>
                  </div>
                ) : (
                  incidentList.map((inc) => (
                    <div
                      key={inc.id}
                      className="p-2.5 rounded-lg bg-ops-bg border border-ops-border hover:border-ops-cyan/50 transition-all cursor-pointer shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="font-semibold text-xs text-white truncate min-w-0 flex-1">
                          {inc.title}
                        </div>
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold shrink-0 whitespace-nowrap leading-none ${
                            inc.severity >= 4
                              ? "bg-red-950 text-ops-red border border-red-800"
                              : "bg-amber-950 text-ops-amber border border-amber-800"
                          }`}
                        >
                          SEV {inc.severity}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-ops-muted mt-2">
                        <span className="font-mono text-[10px]">ID: {inc.id}</span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold shrink-0 whitespace-nowrap leading-none font-mono ${
                            inc.verification_label === "CONFIRMED"
                              ? "text-ops-emerald bg-emerald-950/60 border border-emerald-800/60"
                              : inc.verification_label === "CONFLICTING"
                              ? "text-ops-red bg-red-950/60 border border-red-800/60"
                              : "text-ops-amber bg-amber-950/60 border border-amber-800/60"
                          }`}
                        >
                          {inc.verification_label}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Bottom Half: Fleet Units Section */}
          <div className="h-52 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl shrink-0">
            <div className="h-8 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
              <div className="flex items-center gap-2">
                <Ambulance className="w-3.5 h-3.5 text-ops-cyan" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Fleet Units ({units.length})
                </span>
              </div>
              <span className="text-[10px] font-mono text-ops-muted">Readiness</span>
            </div>

            <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
              {units.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-ops-muted">
                  No fleet units loaded.
                </div>
              ) : (
                units.map((u) => {
                  const typeLabel = (u.unit_type || (u as any).type || "unit").replace("_", " ");
                  return (
                    <div
                      key={u.id}
                      className="flex items-center justify-between py-1 px-2 rounded bg-ops-bg border border-ops-border text-xs"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-ops-cyan uppercase font-bold font-mono text-[11px] shrink-0">{u.id}</span>
                        <span className="text-[11px] text-slate-300 capitalize truncate">{typeLabel}</span>
                      </div>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase shrink-0 whitespace-nowrap leading-none ${
                          u.status === "en_route"
                            ? "bg-amber-950 text-ops-amber border border-amber-800"
                            : u.status === "unavailable"
                            ? "bg-red-950 text-ops-red border border-red-800"
                            : "bg-emerald-950 text-ops-emerald border border-emerald-800"
                        }`}
                      >
                        {u.status}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </section>

        {/* Center Column (5 cols): Dominant Tactical Map Canvas */}
        <section aria-label="Bengaluru Tactical Map" className="col-span-5 flex flex-col min-h-0 shadow-2xl rounded-lg overflow-hidden border border-ops-border">
          <BengaluruTacticalMap />
        </section>

        {/* Right Column (4 cols): Active Dispatch Plan & Multi-Agent Trace */}
        <section aria-label="Plan and Trace Panels" className="col-span-4 flex flex-col gap-2 min-h-0">
          {/* Top Half: Plan & Cost Breakdown with Provisional Approval Checkboxes */}
          <div className="h-64 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-ops-amber" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Active Dispatch Plan
                </span>
              </div>
              {currentPlan && (
                <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800">
                  ID: {currentPlan.plan_id.slice(0, 8)}
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-2.5">
              {currentPlan ? (
                <div className="space-y-2.5">
                  {/* Itemized Cost Breakdown */}
                  <div className="grid grid-cols-3 gap-1.5 p-2 rounded-lg bg-ops-bg border border-ops-border font-mono text-center">
                    <div>
                      <div className="text-[9px] text-slate-400 uppercase">Total Cost</div>
                      <div className="font-bold text-ops-amber text-xs">
                        {(currentPlan.cost_breakdown?.total_cost ?? 0).toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-400 uppercase">Delay Harm</div>
                      <div className="font-semibold text-slate-200 text-xs">
                        {(currentPlan.cost_breakdown?.delay_harm_cost ?? 0).toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-400 uppercase">Wasted Cost</div>
                      <div className="font-semibold text-slate-200 text-xs">
                        {(currentPlan.cost_breakdown?.wasted_dispatch_cost ?? 0).toFixed(1)}
                      </div>
                    </div>
                  </div>

                  {/* Active Assignments List with Provisional Confirmation Checkboxes */}
                  <div className="space-y-1.5">
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                      Assignments ({currentPlan.assignments?.length || 0}):
                    </div>
                    {(currentPlan.assignments || []).map((a) => {
                      const eta = a.eta_minutes ?? a.estimated_eta_minutes ?? 0;
                      const isProvisional = a.is_provisional;

                      return (
                        <div
                          key={`${a.unit_id}-${a.incident_id}`}
                          className={`flex items-center justify-between p-2 rounded-lg border text-xs gap-2 ${
                            isProvisional
                              ? "bg-amber-950/30 border-amber-800/80"
                              : "bg-ops-bg border-ops-border"
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            {isProvisional && (
                              <input
                                type="checkbox"
                                checked={provisionalDecisions[a.unit_id] ?? true}
                                onChange={() => handleDecisionToggle(a.unit_id)}
                                className="w-3.5 h-3.5 rounded border-amber-600 text-amber-500 focus:ring-amber-500 cursor-pointer"
                                title="Explicit Commander Confirmation Required"
                              />
                            )}
                            <span className="text-ops-cyan font-bold font-mono">{a.unit_id}</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="text-white truncate font-medium">{a.incident_id}</span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0 font-mono">
                            <span className="text-slate-400 text-[10px]">ETA {eta.toFixed(0)}m</span>
                            {isProvisional ? (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-950 text-ops-amber border border-amber-800 font-bold">
                                PROVISIONAL
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-ops-emerald border border-emerald-800 font-bold">
                                CONFIRMED
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Quick Approval Action */}
                  <button
                    onClick={handleApprove}
                    disabled={isApproving}
                    className="w-full py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs font-mono transition-colors shadow flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    <FileCheck className="w-4 h-4" />
                    <span>Authorize Dispatch (Ed25519)</span>
                  </button>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center select-none">
                  <Cpu className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
                  <p className="text-xs font-semibold text-slate-300">CP-SAT solver standing by.</p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Start scenario to compute optimal resource allocation plan.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Half: Multi-Agent Message Trace */}
          <div className="flex-1 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-ops-cyan" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Multi-Agent Live Trace ({agentTrace.length})
                </span>
              </div>
              <span className="text-[10px] font-mono text-ops-emerald flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-ops-emerald animate-ping" />
                Live Feed
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1.5 font-mono text-[11px]">
              {agentTrace.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center select-none">
                  <Terminal className="w-8 h-8 text-slate-700 mb-2" />
                  <p className="text-xs font-semibold text-slate-300">Agent bus quiet.</p>
                  <p className="text-[11px] text-slate-500 mt-1">Inter-agent message payloads stream here.</p>
                </div>
              ) : (
                agentTrace.map((msg, idx) => (
                  <div
                    key={`trace-${idx}`}
                    className="p-1.5 rounded bg-ops-bg border border-ops-border flex items-start justify-between gap-2"
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-ops-cyan font-bold shrink-0">{msg.sender}</span>
                      <span className="text-slate-500 shrink-0">&rarr;</span>
                      <span className="text-purple-300 shrink-0">{msg.receiver}</span>
                      <span className="text-slate-400 truncate text-[10px]">[{msg.type}]</span>
                    </div>
                    <span className="text-[9px] text-slate-500 shrink-0">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </main>

      {/* 4. Drawers & Floating Presentation Bar */}
      <AttackPanel />
      <USPProofPanel />
      <PresenterControls />
    </div>
  );
}
