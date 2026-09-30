"use client";

import React from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import {
  ChevronRight,
  ChevronLeft,
  Play,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  Radio,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export interface DemoStep {
  number: number;
  title: string;
  narrative: string;
  highlightTarget: "hero" | "incidents" | "plan" | "approval" | "map" | "veto" | "usp" | "security";
  actionLabel?: string;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    number: 1,
    title: "Scenario Ingestion (T0)",
    narrative: "Three reports arrive during a flood: a crash, a flooded building, a chest-pain call.",
    highlightTarget: "incidents",
    actionLabel: "Start T0 Ingestion",
  },
  {
    number: 2,
    title: "Bayesian Truth Assessment",
    narrative: "Sensors and multiple witnesses CONFIRM the first two. The third has one anonymous source: UNVERIFIED.",
    highlightTarget: "incidents",
  },
  {
    number: 3,
    title: "Uncertainty-Aware Allocation",
    narrative: "CrisisMesh sends a provisional ambulance to the unverified call, so a fake alarm costs little.",
    highlightTarget: "plan",
  },
  {
    number: 4,
    title: "Ed25519 Cryptographic Gate",
    narrative: "The commander approves. The plan is signed and can't be forged.",
    highlightTarget: "approval",
    actionLabel: "Authorize Dispatch",
  },
  {
    number: 5,
    title: "Dynamic Change Events (T+10)",
    narrative: "10 minutes later: a road floods, an ambulance breaks down, a critical new case arrives.",
    highlightTarget: "map",
    actionLabel: "Step T+10",
  },
  {
    number: 6,
    title: "Guardian Route VETO",
    narrative: "The routing agent VETOES a route through the flooded road; the planner re-solves.",
    highlightTarget: "veto",
  },
  {
    number: 7,
    title: "Low-Churn Fleet Stability",
    narrative: "The plan changes as little as possible; en-route units are not pulled away.",
    highlightTarget: "usp",
    actionLabel: "View USP Proof",
  },
  {
    number: 8,
    title: "Multi-Layer Defense",
    narrative: "An attacker sends a fake report and a hidden instruction. Both are BLOCKED. Here is which layer stopped them.",
    highlightTarget: "security",
    actionLabel: "View Attack Feed",
  },
];

interface GuidedNarratorProps {
  currentStep: number;
  onStepChange: (step: number) => void;
  onActionClick?: (step: number) => void;
}

export function GuidedNarrator({ currentStep, onStepChange, onActionClick }: GuidedNarratorProps) {
  const stepData = DEMO_STEPS[currentStep - 1] || DEMO_STEPS[0];

  const handleNext = () => {
    if (currentStep < DEMO_STEPS.length) {
      onStepChange(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      onStepChange(currentStep - 1);
    }
  };

  return (
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 w-[94%] max-w-5xl bg-slate-950/90 border border-cyan-500/40 rounded-xl p-3 shadow-[0_10px_35px_rgba(0,0,0,0.8)] backdrop-blur-xl z-40 flex items-center justify-between gap-4 select-none">
      {/* Step Indicator & Icon */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-9 h-9 rounded-lg bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm shadow-[0_0_12px_rgba(6,182,212,0.3)]">
          {stepData.number}/8
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold">
              GUIDED DEMO • STEP {stepData.number}
            </span>
            <span className="text-[10px] text-slate-400 font-medium">[{stepData.title}]</span>
          </div>
          <p className="text-xs font-semibold text-slate-100 mt-0.5 max-w-2xl leading-relaxed">
            &ldquo;{stepData.narrative}&rdquo;
          </p>
        </div>
      </div>

      {/* Interactive Quick Action & Controls */}
      <div className="flex items-center gap-2 shrink-0">
        {stepData.actionLabel && onActionClick && (
          <button
            onClick={() => onActionClick(currentStep)}
            className="px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs font-mono transition-colors shadow-[0_0_10px_rgba(6,182,212,0.4)] flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{stepData.actionLabel}</span>
          </button>
        )}

        <div className="flex items-center gap-1 bg-slate-900 border border-slate-700 p-0.5 rounded-lg">
          <button
            onClick={handlePrev}
            disabled={currentStep <= 1}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors"
            title="Previous Step"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleNext}
            disabled={currentStep >= DEMO_STEPS.length}
            className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors"
            title="Next Step"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
