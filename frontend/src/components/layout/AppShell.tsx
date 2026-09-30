"use client";

import React, { useEffect, useState } from "react";
import { TopBar } from "./TopBar";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/websocket";
import {
  AlertTriangle,
  Ambulance,
  MapPin,
  GitBranch,
  Terminal,
  Activity,
  Layers,
  Cpu,
} from "lucide-react";

export function AppShell() {
  const {
    activeRole,
    setSnapshot,
    incidents,
    units,
    currentPlan,
    agentTrace,
    isOfflineMap,
    toggleOfflineMap,
    status,
  } = useCrisisStore();

  const [isLoading, setIsLoading] = useState(true);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    async function boot() {
      try {
        setIsLoading(true);
        // 1. Authenticate default role (commander)
        const authData = await api.login("commander", "commander123");
        // 2. Fetch baseline state snapshot
        const snapshot = await api.getState();
        setSnapshot(snapshot);
        // 3. Connect real-time WebSocket client
        wsClient.connect(authData.access_token);
        setIsLoading(false);
      } catch (err: any) {
        console.error("Initialization error:", err);
        setInitError(err.message || "Failed to connect to backend server");
        setIsLoading(false);
      }
    }
    boot();

    return () => {
      wsClient.disconnect();
    };
  }, [setSnapshot]);

  const incidentList = Object.values(incidents);

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-ops-bg text-ops-text select-none">
      {/* 1. Header / Top Bar */}
      <TopBar />

      {/* 2. Main 1080p Non-Scrolling Command Centre Grid */}
      <main className="flex-1 grid grid-cols-12 gap-2 p-2 min-h-0">
        {/* Left Column (3 cols): Incidents & Units */}
        <section
          aria-label="Incidents and Fleet Panel"
          className="col-span-3 flex flex-col gap-2 min-h-0"
        >
          {/* Incidents Section */}
          <div className="flex-1 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-lg">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-ops-red" />
                <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
                  Incidents Queue ({incidentList.length})
                </span>
              </div>
              <span className="text-[10px] font-mono text-ops-muted">Severity / Truth</span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {incidentList.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4 text-ops-muted">
                  <Activity className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
                  <p className="text-xs font-mono">No active incidents reported.</p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Click &apos;Start T0&apos; in header to ingest flood reports.
                  </p>
                </div>
              ) : (
                incidentList.map((inc) => (
                  <div
                    key={inc.id}
                    className="p-2.5 rounded bg-ops-bg border border-ops-border hover:border-ops-borderBright transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-semibold text-xs text-white truncate">{inc.title}</div>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-bold ${
                          inc.severity >= 4
                            ? "bg-red-950 text-ops-red border border-red-800"
                            : "bg-amber-950 text-ops-amber border border-amber-800"
                        }`}
                      >
                        SEV {inc.severity}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono text-ops-muted mt-2">
                      <span>Affected: {inc.people_affected}</span>
                      <span
                        className={`px-1 rounded text-[10px] ${
                          inc.verification_label === "CONFIRMED"
                            ? "text-ops-emerald bg-emerald-950/60"
                            : inc.verification_label === "CONFLICTING"
                            ? "text-ops-red bg-red-950/60"
                            : "text-ops-amber bg-amber-950/60"
                        }`}
                      >
                        {inc.verification_label}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Units Section */}
          <div className="h-44 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-lg">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50">
              <div className="flex items-center gap-2">
                <Ambulance className="w-4 h-4 text-ops-cyan" />
                <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
                  Fleet Units ({units.length})
                </span>
              </div>
              <span className="text-[10px] font-mono text-ops-muted">Status</span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {units.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs font-mono text-ops-muted">
                  No fleet units loaded.
                </div>
              ) : (
                units.map((u) => (
                  <div
                    key={u.id}
                    className="flex items-center justify-between p-1.5 px-2 rounded bg-ops-bg border border-ops-border text-xs font-mono"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-ops-cyan uppercase font-bold">{u.id}</span>
                      <span className="text-[11px] text-slate-400 capitalize">{u.type}</span>
                    </div>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase ${
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
                ))
              )}
            </div>
          </div>
        </section>

        {/* Center Column (5 cols): Tactical Map Canvas */}
        <section
          aria-label="Bengaluru Flood Map"
          className="col-span-5 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden relative shadow-xl"
        >
          {/* Map Controls Header */}
          <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 z-10">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-ops-emerald" />
              <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
                Bengaluru Tactical Map
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={toggleOfflineMap}
                className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-ops-bg border border-ops-border hover:border-ops-borderBright text-slate-300"
              >
                <Layers className="w-3 h-3 text-ops-cyan" />
                <span>{isOfflineMap ? "Mode: Offline Vector" : "Mode: MapLibre GL"}</span>
              </button>
            </div>
          </div>

          {/* Map Viewport Placeholder (Step 2 integrates MapLibre & Canvas) */}
          <div className="flex-1 bg-[#070a0f] relative flex flex-col items-center justify-center p-6 text-center">
            <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />

            <div className="z-10 flex flex-col items-center max-w-sm">
              <div className="w-16 h-16 rounded-full bg-blue-950/40 border border-blue-600/50 flex items-center justify-center text-ops-cyan mb-4 shadow-[0_0_24px_rgba(6,182,212,0.2)]">
                <MapPin className="w-8 h-8 animate-bounce text-ops-cyan" />
              </div>
              <h3 className="font-mono text-sm font-bold text-white tracking-wider uppercase mb-1">
                Active Tactical Zone
              </h3>
              <p className="text-xs font-mono text-slate-400 mb-3">
                Bengaluru Outer Ring Road &bull; Silk Board &bull; Bellandur &bull; Koramangala
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center font-mono text-[11px]">
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Incidents: {incidentList.length}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Fleet: {units.length}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Assignments: {currentPlan?.assignments.length || 0}
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-mono mt-4">
                Step 2 will render live WebGL markers, animated dispatch vectors, and road flooding.
              </p>
            </div>
          </div>
        </section>

        {/* Right Column (4 cols): Plan Diff & Agent Trace */}
        <section
          aria-label="Plan and Agent Trace Panel"
          className="col-span-4 flex flex-col gap-2 min-h-0"
        >
          {/* Top Half: Plan & Cost Breakdown */}
          <div className="h-64 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-lg">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-ops-amber" />
                <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
                  Active Dispatch Plan
                </span>
              </div>
              <span className="text-[10px] font-mono text-ops-muted">
                {currentPlan ? `ID: ${currentPlan.plan_id.slice(0, 8)}` : "No Plan"}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 font-mono text-xs">
              {currentPlan ? (
                <div className="space-y-2">
                  {/* Cost Summary */}
                  <div className="grid grid-cols-3 gap-1.5 bg-ops-bg p-2 rounded border border-ops-border text-center">
                    <div>
                      <div className="text-[10px] text-ops-muted uppercase">Total Cost</div>
                      <div className="font-bold text-ops-amber">
                        {currentPlan.cost_breakdown.total_cost.toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-ops-muted uppercase">Delay Harm</div>
                      <div className="font-semibold text-slate-200">
                        {currentPlan.cost_breakdown.delay_harm.toFixed(1)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-ops-muted uppercase">Wasted Cost</div>
                      <div className="font-semibold text-slate-200">
                        {currentPlan.cost_breakdown.wasted_cost.toFixed(1)}
                      </div>
                    </div>
                  </div>

                  {/* Active Assignments */}
                  <div className="space-y-1">
                    <div className="text-[11px] text-slate-400 font-semibold uppercase">
                      Assignments ({currentPlan.assignments.length}):
                    </div>
                    {currentPlan.assignments.map((a) => (
                      <div
                        key={`${a.unit_id}-${a.incident_id}`}
                        className="flex items-center justify-between p-1.5 rounded bg-ops-bg border border-ops-border text-[11px]"
                      >
                        <span className="text-ops-cyan font-bold">{a.unit_id}</span>
                        <span className="text-slate-500">&rarr;</span>
                        <span className="text-white">{a.incident_id}</span>
                        <span className="text-ops-muted">ETA {a.estimated_eta_minutes.toFixed(0)}m</span>
                        {a.is_provisional && (
                          <span className="text-[9px] px-1 rounded bg-amber-950 text-ops-amber border border-amber-800">
                            PROVISIONAL
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center">
                  <Cpu className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
                  <p>CP-SAT solver standing by.</p>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Start scenario or report incident to generate plan.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Half: Multi-Agent Message Trace */}
          <div className="flex-1 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-lg">
            <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-ops-cyan" />
                <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
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
                <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center">
                  <Terminal className="w-8 h-8 text-slate-700 mb-2" />
                  <p>Agent bus quiet.</p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    All 7 agents communicate via typed bus messages.
                  </p>
                </div>
              ) : (
                agentTrace.map((msg, idx) => (
                  <div
                    key={`${msg.timestamp}-${idx}`}
                    className="p-1.5 rounded bg-ops-bg border border-ops-border flex flex-col gap-0.5"
                  >
                    <div className="flex items-center justify-between text-[10px]">
                      <div className="flex items-center gap-1.5 font-bold">
                        <span className="text-ops-cyan">{msg.sender}</span>
                        <span className="text-slate-600">&rarr;</span>
                        <span className="text-ops-amber">{msg.receiver}</span>
                      </div>
                      <span className="text-slate-500">
                        {new Date(msg.timestamp * 1000).toLocaleTimeString("en-GB")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-300">
                      <span className="font-semibold text-ops-emerald">{msg.type}</span>
                      <span className="text-slate-500 truncate max-w-[150px]">
                        {msg.trace_id.slice(0, 10)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
