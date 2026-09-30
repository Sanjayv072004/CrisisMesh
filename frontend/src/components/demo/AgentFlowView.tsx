"use client";

import React from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import {
  ShieldAlert,
  BrainCircuit,
  Eye,
  Activity,
  MapPin,
  Cpu,
  ShieldCheck,
  Megaphone,
  Radio,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export function AgentFlowView() {
  const { agentTrace, status, currentPlan } = useCrisisStore();

  const agents = [
    { id: "Supervisor", label: "Supervisor", icon: BrainCircuit, color: "text-purple-400", border: "border-purple-500" },
    { id: "Situation", label: "Situation (Quarantine)", icon: Eye, color: "text-blue-400", border: "border-blue-500" },
    { id: "Verification", label: "Verification (Bayesian)", icon: Activity, color: "text-emerald-400", border: "border-emerald-500" },
    { id: "Impact", label: "Impact (Road Graph)", icon: MapPin, color: "text-amber-400", border: "border-amber-500" },
    { id: "Resource", label: "Resource (CP-SAT)", icon: Cpu, color: "text-cyan-400", border: "border-cyan-500" },
    { id: "Guardian", label: "Guardian (Safety)", icon: ShieldCheck, color: "text-rose-400", border: "border-rose-500" },
    { id: "Command", label: "Command (Briefing)", icon: Radio, color: "text-indigo-400", border: "border-indigo-500" },
    { id: "Comm", label: "Comm (Advisory)", icon: Megaphone, color: "text-teal-400", border: "border-teal-500" },
  ];

  // Check if veto occurred in trace
  const hasVeto = agentTrace.some(
    (m) => m.type === "PlanVeto" || (m.payload && (m.payload as any).veto_reason)
  );

  const lastMessage = agentTrace[agentTrace.length - 1];

  return (
    <div className="w-full bg-ops-surface border border-ops-border rounded-lg p-3 shadow-xl select-none">
      <div className="flex items-center justify-between pb-2 border-b border-ops-border mb-3">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-ops-cyan" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-slate-200">
            Multi-Agent State Flow & Veto Negotiation Graph
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-[11px]">
          {hasVeto ? (
            <span className="flex items-center gap-1 text-ops-red bg-red-950/80 px-2 py-0.5 rounded border border-red-700 font-bold animate-pulse">
              <RotateCcw className="w-3.5 h-3.5" />
              <span>IMPACT VETO RE-SOLVE TRIGGERED</span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-ops-emerald bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>CONSENSUS PIPELINE ACTIVE</span>
            </span>
          )}
        </div>
      </div>

      {/* Workflow Horizontal Node Flow */}
      <div className="grid grid-cols-8 gap-2 relative">
        {agents.map((agent, index) => {
          const Icon = agent.icon;
          const isSender = lastMessage?.sender?.toLowerCase().includes(agent.id.toLowerCase());
          const isReceiver = lastMessage?.receiver?.toLowerCase().includes(agent.id.toLowerCase());
          const isActing = isSender || isReceiver;

          return (
            <div
              key={agent.id}
              className={`flex flex-col items-center text-center p-2 rounded-lg border transition-all duration-300 relative ${
                isActing
                  ? `bg-slate-800/90 ${agent.border} shadow-[0_0_15px_rgba(56,189,248,0.25)] scale-105`
                  : "bg-ops-bg/80 border-ops-border text-slate-400"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center mb-1.5 ${
                  isActing ? "bg-slate-700 " + agent.color : "bg-slate-900 text-slate-500"
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>

              <span className={`text-[10px] font-bold truncate max-w-full ${isActing ? "text-white" : "text-slate-300"}`}>
                {agent.label.split(" ")[0]}
              </span>
              <span className="text-[9px] text-slate-400 truncate max-w-full">
                {agent.label.split(" ")[1] || ""}
              </span>

              {/* Status Ping */}
              {isActing && (
                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Veto Loop Arrow Explanation */}
      {hasVeto && (
        <div className="mt-2.5 p-1.5 rounded bg-rose-950/40 border border-rose-800/60 flex items-center justify-between text-[11px] font-mono text-rose-200">
          <div className="flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Veto Negotiation:</strong> ImpactAgent detected flooded road approach &rarr; Vetoed route &rarr; ResourceAgent re-solved allocation under added constraint.
            </span>
          </div>
          <span className="text-ops-cyan font-bold">Round 1/3</span>
        </div>
      )}
    </div>
  );
}
