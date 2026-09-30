"use client";

import React from "react";
import { Play, Shield, Activity, GitBranch, Terminal, Cpu, ArrowRight } from "lucide-react";

interface HeroIntroModalProps {
  onStartDemo: () => void;
  onExploreFreely: () => void;
}

export function HeroIntroModal({ onStartDemo, onExploreFreely }: HeroIntroModalProps) {
  return (
    <div className="fixed inset-0 bg-[#050811]/90 backdrop-blur-md z-50 flex items-center justify-center p-4 select-none">
      <div className="max-w-2xl w-full bg-slate-950/90 border border-cyan-500/40 rounded-2xl p-8 shadow-[0_20px_60px_rgba(0,0,0,0.9)] flex flex-col items-center text-center relative overflow-hidden">
        {/* Glow ambient circle */}
        <div className="absolute -top-24 -left-24 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/50 text-cyan-300 font-mono text-xs mb-4">
          <Activity className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
          <span>GATEWAYS 2026 • CRISIS RECOVERY SYSTEM</span>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl font-sans">
          CRISISMESH
        </h1>
        <p className="mt-2 text-sm text-cyan-400 font-mono font-medium uppercase tracking-wider">
          Autonomous Emergency Coordination & Tactical Command
        </p>

        {/* One-line Pitch */}
        <p className="mt-4 text-slate-300 text-sm max-w-lg leading-relaxed">
          Multi-agent flood response for Bengaluru featuring Bayesian verification, CP-SAT low-churn allocation, unscripted Guardian route VETO, and Ed25519 cryptographic approval.
        </p>

        {/* 3 Value Pillars */}
        <div className="grid grid-cols-3 gap-3 my-6 w-full text-left font-mono">
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
            <Cpu className="w-4 h-4 text-cyan-400 mb-1.5" />
            <div className="text-xs font-bold text-slate-200">CP-SAT Solver</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Low-churn fleet stability (&lambda;=60)</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
            <GitBranch className="w-4 h-4 text-amber-400 mb-1.5" />
            <div className="text-xs font-bold text-slate-200">8-Agent Mesh</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Unscripted Guardian VETO loop</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
            <Shield className="w-4 h-4 text-emerald-400 mb-1.5" />
            <div className="text-xs font-bold text-slate-200">Ed25519 & Audit</div>
            <div className="text-[10px] text-slate-400 mt-0.5">SHA-256 tamper-evident chain</div>
          </div>
        </div>

        {/* Primary Call to Action */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={onStartDemo}
            className="flex-1 sm:flex-initial px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold font-mono text-sm shadow-[0_0_20px_rgba(6,182,212,0.5)] transition-all flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Run Guided Demo</span>
          </button>
          <button
            onClick={onExploreFreely}
            className="px-4 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-mono text-xs border border-slate-700 transition-colors"
          >
            Explore Manually
          </button>
        </div>
      </div>
    </div>
  );
}
