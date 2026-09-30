"use client";

import React, { useEffect, useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/websocket";
import { Role } from "@/types";
import {
  ShieldAlert,
  ShieldCheck,
  Radio,
  Clock,
  RotateCcw,
  Play,
  FastForward,
  UserCheck,
  Server,
} from "lucide-react";

export function TopBar() {
  const {
    status,
    activeRole,
    setActiveRole,
    connectionStatus,
    auditStatus,
    setSnapshot,
    setAuditStatus,
  } = useCrisisStore();

  const [timeStr, setTimeStr] = useState<string>("");
  const [isActing, setIsActing] = useState(false);

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString("en-GB", { hour12: false }));
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // Role switch handler
  const handleRoleChange = async (newRole: Role) => {
    try {
      const pass = newRole === "viewer" ? "viewer123" : newRole === "operator" ? "operator123" : "commander123";
      const res = await api.login(newRole, pass);
      setActiveRole(newRole);
      wsClient.connect(res.access_token);
    } catch (e) {
      console.error("Failed to switch role:", e);
    }
  };

  // Scenario actions
  const handleReset = async () => {
    setIsActing(true);
    try {
      const snap = await api.resetScenario();
      setSnapshot(snap);
      const audit = await api.verifyAudit();
      setAuditStatus(audit);
    } catch (e) {
      console.error(e);
    } finally {
      setIsActing(false);
    }
  };

  const handleStart = async () => {
    setIsActing(true);
    try {
      const snap = await api.startScenario();
      setSnapshot(snap);
    } catch (e) {
      console.error(e);
    } finally {
      setIsActing(false);
    }
  };

  const handleStep = async () => {
    setIsActing(true);
    try {
      const snap = await api.stepScenario();
      setSnapshot(snap);
    } catch (e) {
      console.error(e);
    } finally {
      setIsActing(false);
    }
  };

  return (
    <header className="h-14 bg-ops-surface border-b border-ops-border flex items-center justify-between px-4 select-none">
      {/* Brand & Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-red-950/80 border border-ops-red flex items-center justify-center text-ops-red shadow-[0_0_12px_rgba(239,68,68,0.4)]">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wider uppercase text-ops-text font-mono">
                CRISISMESH
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-950 text-ops-cyan border border-blue-800">
                Ops Centre
              </span>
            </div>
            <div className="text-[10px] text-ops-muted font-mono">Bengaluru Flood Command</div>
          </div>
        </div>

        {/* Vertical divider */}
        <div className="h-6 w-px bg-ops-border" />

        {/* Operational State Badge */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-ops-muted text-[11px]">STATE:</span>
          <span
            className={`px-2 py-0.5 rounded border text-[11px] font-semibold tracking-wide ${
              status === "DISPATCHED"
                ? "bg-emerald-950/80 text-ops-emerald border-emerald-700"
                : status === "AWAITING_COMMANDER_APPROVAL"
                ? "bg-amber-950/80 text-ops-amber border-amber-600 animate-pulse"
                : "bg-slate-900 text-slate-300 border-slate-700"
            }`}
          >
            {status}
          </span>
        </div>
      </div>

      {/* Scenario Controls */}
      <div className="flex items-center gap-1.5 bg-ops-bg border border-ops-border p-1 rounded-md">
        <button
          onClick={handleReset}
          disabled={isActing}
          title="Reset to clean baseline scenario"
          className="flex items-center gap-1 px-2 py-1 text-xs font-mono rounded text-slate-300 hover:text-white hover:bg-ops-surfaceHover disabled:opacity-50 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
        <button
          onClick={handleStart}
          disabled={isActing}
          title="Inject T0 Incidents (Silk Board, Bellandur, Koramangala)"
          className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded bg-blue-950 text-ops-cyan border border-blue-800 hover:bg-blue-900 disabled:opacity-50 transition-colors font-medium"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Start T0</span>
        </button>
        <button
          onClick={handleStep}
          disabled={isActing}
          title="Inject T+10 events (Outer Ring Road underpass trapped SUV + Amb 2 engine failure)"
          className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded bg-amber-950 text-ops-amber border border-amber-800 hover:bg-amber-900 disabled:opacity-50 transition-colors font-medium"
        >
          <FastForward className="w-3.5 h-3.5 fill-current" />
          <span>Step T+10</span>
        </button>
      </div>

      {/* Telemetry, Security & Role */}
      <div className="flex items-center gap-4">
        {/* Clock */}
        <div className="flex items-center gap-1.5 text-xs font-mono text-ops-muted">
          <Clock className="w-3.5 h-3.5 text-ops-cyan" />
          <span>{timeStr || "00:00:00"} IST</span>
        </div>

        {/* Audit Status */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          {auditStatus.is_valid ? (
            <span className="flex items-center gap-1 text-ops-emerald" title="Cryptographic SHA-256 chain valid">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span className="text-[11px]">AUDIT: OK ({auditStatus.total_entries})</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-ops-red font-bold animate-pulse" title="Tampering detected!">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span className="text-[11px]">AUDIT: BROKEN</span>
            </span>
          )}
        </div>

        {/* WebSocket Connection */}
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <div
            className={`w-2 h-2 rounded-full ${
              connectionStatus === "CONNECTED"
                ? "bg-ops-emerald shadow-[0_0_8px_#10b981]"
                : connectionStatus === "CONNECTING"
                ? "bg-ops-amber animate-ping"
                : "bg-ops-red"
            }`}
          />
          <span className="text-[11px] text-ops-muted">{connectionStatus}</span>
        </div>

        {/* Mode Badge */}
        <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400">
          <Server className="w-3 h-3 text-ops-cyan" />
          <span>MOCK</span>
        </div>

        {/* Role Selector */}
        <div className="flex items-center gap-1.5 bg-ops-bg border border-ops-border px-2 py-1 rounded">
          <UserCheck className="w-3.5 h-3.5 text-ops-amber" />
          <span className="text-[11px] font-mono text-ops-muted">ROLE:</span>
          <select
            value={activeRole}
            onChange={(e) => handleRoleChange(e.target.value as Role)}
            className="bg-transparent text-xs font-mono font-semibold uppercase text-ops-amber outline-none cursor-pointer"
          >
            <option value="viewer" className="bg-ops-surface text-slate-300">
              Viewer
            </option>
            <option value="operator" className="bg-ops-surface text-ops-cyan">
              Operator
            </option>
            <option value="commander" className="bg-ops-surface text-ops-amber">
              Commander
            </option>
          </select>
        </div>
      </div>
    </header>
  );
}
