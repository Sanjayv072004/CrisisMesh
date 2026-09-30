"use client";

import React, { useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import {
  Shield,
  Activity,
  Cpu,
  Radio,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
  GitBranch,
  Flame,
  ArrowRight,
  RotateCcw,
} from "lucide-react";

interface AgentDef {
  name: string;
  role: string;
  short: string;
  icon: React.ElementType;
}

const AGENTS: AgentDef[] = [
  { name: "Supervisor", role: "Routing Orchestrator", short: "SUP", icon: Activity },
  { name: "Situation", role: "Report Ingestion", short: "SIT", icon: Flame },
  { name: "Verification", role: "Truth & Credibility", short: "VER", icon: CheckCircle2 },
  { name: "Impact", role: "Hospital & Roads", short: "IMP", icon: AlertTriangle },
  { name: "Resource", role: "CP-SAT Allocation", short: "RES", icon: Cpu },
  { name: "Guardian", role: "Safety & Invariants", short: "GRD", icon: Shield },
  { name: "Command", role: "Approval Packaging", short: "CMD", icon: FileCheck },
  { name: "Comm", role: "Public & Unit Advisory", short: "COM", icon: Radio },
];

export function AgentMeshStrip() {
  const { agentTrace, status, currentPlan, planDiff } = useCrisisStore();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // Determine active agent from latest message trace
  const latestMsg = agentTrace[0];
  const activeAgentName = latestMsg?.sender || (status === "RUNNING_T0" ? "Resource" : "Command");

  // Detect unscripted VETO in trace
  const hasVeto = agentTrace.some(
    (m) =>
      m.type === "RouteVetoed" ||
      m.type === "PlanVetoed" ||
      (m.sender === "Guardian" && m.receiver === "Resource") ||
      (m.payload && JSON.stringify(m.payload).includes("veto"))
  );

  return (
    <div className="w-full bg-slate-950/80 border border-ops-border rounded-lg px-3 py-1.5 flex items-center justify-between gap-2 shadow-lg backdrop-blur select-none">
      {/* Label */}
      <div className="flex items-center gap-1.5 shrink-0 font-mono text-[11px]">
        <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span className="font-bold text-slate-200 uppercase tracking-wider">AGENT MESH</span>
      </div>

      {/* Horizontal Agent Nodes Flow */}
      <div className="flex-1 flex items-center justify-center gap-1 overflow-x-auto py-0.5">
        {AGENTS.map((ag, idx) => {
          const Icon = ag.icon;
          const isActive = activeAgentName.toLowerCase().includes(ag.name.toLowerCase());
          const isGuardian = ag.name === "Guardian";
          const isResource = ag.name === "Resource";
          const isVetoActive = hasVeto && (isGuardian || isResource);

          return (
            <React.Fragment key={ag.name}>
              <div
                onClick={() => setSelectedAgent(selectedAgent === ag.name ? null : ag.name)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-mono cursor-pointer transition-all ${
                  isVetoActive
                    ? "bg-red-950/80 border border-red-500 text-red-300 shadow-[0_0_10px_rgba(239,68,68,0.4)] animate-pulse"
                    : isActive
                    ? "bg-cyan-950/80 border border-cyan-500 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.3)]"
                    : "bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
                title={`${ag.name}: ${ag.role}`}
              >
                <Icon className={`w-3.5 h-3.5 ${isVetoActive ? "text-red-400" : isActive ? "text-cyan-400" : "text-slate-500"}`} />
                <span className="font-semibold">{ag.short}</span>
              </div>

              {idx < AGENTS.length - 1 && (
                <div className="text-slate-600 font-mono text-[10px] shrink-0">
                  {isGuardian && hasVeto ? (
                    <span className="text-red-400 font-bold px-0.5 animate-bounce">&larr; VETO</span>
                  ) : (
                    <span>&rarr;</span>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* VETO / Re-Solve Indicator Tag */}
      <div className="shrink-0 font-mono text-[10px]">
        {hasVeto ? (
          <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-bold animate-pulse">
            VETO &bull; RE-SOLVED
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            BUS: IDLE
          </span>
        )}
      </div>
    </div>
  );
}
