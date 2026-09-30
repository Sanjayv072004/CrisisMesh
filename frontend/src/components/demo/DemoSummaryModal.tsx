"use client";

import React from "react";
import { CheckCircle2, ShieldCheck, Cpu, ArrowRight, RotateCcw } from "lucide-react";

interface DemoSummaryModalProps {
  onRestart: () => void;
  onClose: () => void;
}

export function DemoSummaryModal({ onRestart, onClose }: DemoSummaryModalProps) {
  return (
    <div className="fixed inset-0 bg-[#050811]/90 backdrop-blur-md z-50 flex items-center justify-center p-4 select-none">
      <div className="max-w-xl w-full bg-slate-950/90 border border-emerald-500/40 rounded-2xl p-6 shadow-[0_20px_60px_rgba(0,0,0,0.9)] flex flex-col items-center text-center">
        <div className="w-12 h-12 rounded-full bg-emerald-950 border border-emerald-500 flex items-center justify-center text-emerald-400 mb-3 shadow-[0_0_15px_rgba(16,185,129,0.4)]">
          <CheckCircle2 className="w-6 h-6" />
        </div>

        <h2 className="text-2xl font-bold text-white font-sans">
          Mission Completed • Demo Verified
        </h2>
        <p className="text-xs text-slate-400 font-mono mt-1">
          Full 8-Step Autonomous Crisis Response Trajectory Executed
        </p>

        {/* Verification Summary Grid */}
        <div className="grid grid-cols-2 gap-3 my-5 w-full text-left font-mono text-xs">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Unscripted Veto</div>
            <div className="font-bold text-emerald-400 text-sm mt-0.5">Route Blockage Detected</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Guardian &rarr; Resource Re-solve</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Low-Churn Stability</div>
            <div className="font-bold text-emerald-400 text-sm mt-0.5">0 En-Route Pullaways</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Idle fleet mobilized instead</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Cryptographic Gate</div>
            <div className="font-bold text-cyan-400 text-sm mt-0.5">Ed25519 Signed</div>
            <div className="text-[10px] text-slate-400 mt-0.5">SHA-256 Audit chain valid</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-slate-400 text-[10px] uppercase">Adversarial Defense</div>
            <div className="font-bold text-cyan-400 text-sm mt-0.5">100% Contained</div>
            <div className="text-[10px] text-slate-400 mt-0.5">0 Quarantined dispatches</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onRestart}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-600 flex items-center gap-1.5 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Restart Demo</span>
          </button>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold shadow-[0_0_12px_rgba(16,185,129,0.4)] transition-colors"
          >
            Explore Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
