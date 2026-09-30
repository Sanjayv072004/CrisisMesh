"use client";

import React from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { AlertCircle } from "lucide-react";

export function SafeModeBanner() {
  const { isSafeMode, toggleSafeMode } = useCrisisStore();

  if (!isSafeMode) {
    return (
      <div className="bg-slate-900/90 border-b border-amber-500/30 px-4 py-1.5 flex items-center justify-between text-xs text-amber-300">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          <span>LIVE CLOUD MODE: Live LLM and live map tiles active. Click to switch to Safe Mode.</span>
        </div>
        <button
          onClick={toggleSafeMode}
          className="px-2.5 py-0.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 text-[11px] font-mono transition-colors"
        >
          Enable Safe Mode
        </button>
      </div>
    );
  }

  return (
    <div className="bg-cyan-950/90 border-b border-cyan-500/40 px-4 py-1.5 flex items-center justify-between text-xs text-cyan-200 shadow-md">
      <div className="flex items-center gap-2 font-mono">
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
        </span>
        <span className="font-bold tracking-wider text-cyan-300">[SAFE MODE ACTIVE]</span>
        <span className="text-cyan-400/80">Deterministic Fallback: Mock LLM • Bengaluru Tactical Graph (9 nodes, 12 corridors) • Offline Vector Grid • &lt; 4m Guarantee</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[11px] text-cyan-400/60 hidden sm:inline">Hotkey: [P]resenter</span>
        <button
          onClick={toggleSafeMode}
          className="px-2.5 py-0.5 rounded bg-cyan-800/40 hover:bg-cyan-800/60 text-cyan-300 border border-cyan-500/50 text-[11px] font-mono transition-colors"
        >
          Disable Safe Mode
        </button>
      </div>
    </div>
  );
}
