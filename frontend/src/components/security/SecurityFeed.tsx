"use client";

import React from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { ShieldAlert, ShieldCheck, Lock, AlertOctagon, Terminal } from "lucide-react";

export function SecurityFeed() {
  const { securityEvents, lastAttackOutcome } = useCrisisStore();

  return (
    <div className="flex-1 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-lg select-none">
      <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-ops-red" />
          <span className="font-mono text-xs font-semibold tracking-wider uppercase text-slate-200">
            Security & Quarantine Feed ({securityEvents.length})
          </span>
        </div>
        <span className="text-[10px] font-mono text-ops-emerald flex items-center gap-1">
          <Lock className="w-3 h-3 text-ops-emerald" />
          Zero-Trust Ingestion
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2 font-mono text-xs">
        {/* If last attack was simulated */}
        {lastAttackOutcome && (
          <div className="p-2.5 rounded bg-rose-950/70 border border-rose-500/80 shadow-md">
            <div className="flex items-center justify-between font-bold text-rose-300 text-[11px] mb-1">
              <span className="uppercase tracking-wider">Attack Vector: {lastAttackOutcome.attack_type}</span>
              <span className="px-1.5 py-0.2 rounded bg-rose-900 border border-rose-600 text-white text-[10px]">
                {lastAttackOutcome.result}
              </span>
            </div>
            <div className="text-[11px] text-slate-300">
              <span className="text-slate-400">Mitigating Layer:</span> {lastAttackOutcome.mitigating_layer}
            </div>
            <p className="text-[10px] text-rose-200 mt-1">{lastAttackOutcome.detail}</p>
          </div>
        )}

        {securityEvents.length === 0 && !lastAttackOutcome ? (
          <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center">
            <ShieldCheck className="w-8 h-8 text-slate-700 mb-2" />
            <p className="text-xs">Zero security violations detected.</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Prompt injections, botnet floods, and forged keys are automatically quarantined here.
            </p>
          </div>
        ) : (
          securityEvents.map((evt, idx) => (
            <div
              key={`sec-evt-${idx}`}
              className="p-2 rounded bg-ops-bg border border-ops-border text-[11px] space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="text-ops-red font-bold uppercase">{evt.event_type}</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-red-950 text-red-300 border border-red-800">
                  {evt.severity || "HIGH"}
                </span>
              </div>
              <div className="text-slate-300">{evt.description}</div>
              <div className="text-[10px] text-ops-muted flex items-center justify-between pt-1 border-t border-ops-border/60">
                <span>Layer: {evt.agent_name || "IngestionGateway"}</span>
                <span>QUARANTINED (0 Assignments)</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
