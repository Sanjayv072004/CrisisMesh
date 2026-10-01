"use client";

import React from "react";
import { Play, Shield, Activity, GitBranch, Terminal, Cpu, ArrowRight } from "lucide-react";

interface HeroIntroModalProps {
  onStartDemo: () => void;
  onExploreFreely: () => void;
}

export function HeroIntroModal({ onStartDemo, onExploreFreely }: HeroIntroModalProps) {
  return (
    <div className="fixed inset-0 bg-[#070814]/85 backdrop-blur-xl z-50 flex items-center justify-center p-4 select-none">
      <div className="max-w-2xl w-full glass-panel rounded-2xl p-8 shadow-[0_25px_70px_rgba(0,0,0,0.8)] flex flex-col items-center text-center relative overflow-hidden border border-ops-border">
        {/* Glow ambient circle */}
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-ops-violet/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-72 h-72 bg-ops-lime/10 rounded-full blur-3xl pointer-events-none" />

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-ops-surface border border-ops-borderBright text-violet-300 font-mono text-xs mb-4 shadow-inner">
          <Activity className="w-3.5 h-3.5 animate-pulse text-ops-lime" />
          <span className="tracking-wide">GATEWAYS 2026 • CRISIS RECOVERY SYSTEM</span>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl font-sans">
          CRISISMESH
        </h1>
        <p className="mt-2 text-xs text-ops-lime font-mono font-bold uppercase tracking-widest">
          Autonomous Emergency Coordination & Tactical Command
        </p>

        {/* One-line Pitch */}
        <p className="mt-4 text-slate-300 text-sm max-w-lg leading-relaxed font-sans">
          Multi-agent flood response for Bengaluru featuring Bayesian verification, CP-SAT low-churn allocation, unscripted Guardian route VETO, and Ed25519 cryptographic approval.
        </p>

        {/* 3 Value Pillars */}
        <div className="grid grid-cols-3 gap-3 my-6 w-full text-left font-mono">
          <div className="p-3.5 rounded-xl glass-card border border-ops-border">
            <Cpu className="w-4 h-4 text-ops-lime mb-1.5" />
            <div className="text-xs font-bold text-slate-100">CP-SAT Solver</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Low-churn fleet stability (&lambda;=60)</div>
          </div>
          <div className="p-3.5 rounded-xl glass-card border border-ops-border">
            <GitBranch className="w-4 h-4 text-amber-400 mb-1.5" />
            <div className="text-xs font-bold text-slate-100">8-Agent Mesh</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Unscripted Guardian VETO loop</div>
          </div>
          <div className="p-3.5 rounded-xl glass-card border border-ops-border">
            <Shield className="w-4 h-4 text-emerald-400 mb-1.5" />
            <div className="text-xs font-bold text-slate-100">Ed25519 & Audit</div>
            <div className="text-[10px] text-slate-400 mt-0.5">SHA-256 tamper-evident chain</div>
          </div>
        </div>

        {/* Primary Call to Action */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={onStartDemo}
            className="flex-1 sm:flex-initial px-6 py-3 rounded-xl bg-ops-lime hover:bg-ops-limeHover text-slate-950 font-extrabold font-mono text-xs uppercase tracking-wider shadow-[0_0_25px_rgba(198,244,50,0.4)] transition-all flex items-center justify-center gap-2 transform active:scale-95"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Run Guided Demo</span>
          </button>
          <button
            onClick={onExploreFreely}
            className="px-5 py-3 rounded-xl bg-ops-surface hover:bg-ops-surfaceHover text-slate-300 font-mono text-xs border border-ops-border transition-colors font-medium"
          >
            Explore Manually
          </button>
        </div>
      </div>
    </div>
  );
}
