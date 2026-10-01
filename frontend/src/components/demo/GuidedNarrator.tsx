"use client";

import React from "react";
import {
  ChevronRight,
  ChevronLeft,
  Sparkles,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

export interface DemoStep {
  number: number;
  title: string;
  narrative: string;
  instruction: string;
  actionLabel?: string;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    number: 1,
    title: "1. Flood Emergencies Arrive",
    narrative: "Three 112 emergency calls arrive during a Bengaluru flash flood: a multi-vehicle crash, a flooded apartment basement, and a home cardiac call.",
    instruction: "Look at the LEFT panel ('Emergencies'). Click 'Start Scenario' or 'Next' to ingest the calls.",
    actionLabel: "Start Scenario",
  },
  {
    number: 2,
    title: "2. Automatic AI Verification",
    narrative: "CrisisMesh checks physical flood sensors and witness reports. Silk Board and Bellandur are CONFIRMED (Green). Koramangala is UNVERIFIED (Amber single caller).",
    instruction: "Notice the plain trust chips on the left. Unconfirmed reports never get full irreversible dispatches.",
  },
  {
    number: 3,
    title: "3. Recommended Response",
    narrative: "On the RIGHT ('What we recommend'), our solver calculates the fastest routes. The unverified call receives a PROVISIONAL ambulance with a confirmation checkbox.",
    instruction: "Click 'Why this choice?' under any unit to see why it was chosen over runner-up ambulances.",
  },
  {
    number: 4,
    title: "4. Commander Authorization",
    narrative: "The commander reviews the recommendations and signs the orders with a secure Ed25519 cryptographic key.",
    instruction: "Click the green 'Approve & Dispatch Plan' button on the right to authorize the fleet.",
    actionLabel: "Approve & Dispatch",
  },
  {
    number: 5,
    title: "5. Dynamic Flood Events (T+10)",
    narrative: "10 minutes later: Outer Ring Road floods (2.5m depth), an ambulance breaks down, and an SUV gets trapped in the underpass.",
    instruction: "Click 'Step T+10' or 'Next' to trigger the real-time flood blockage.",
    actionLabel: "Step T+10",
  },
  {
    number: 6,
    title: "6. Tactical Veto & Auto-Reroute",
    narrative: "The Impact AI detects the road blockage and immediately VETOES the direct path. The planner auto-reroutes rescue teams safely via Ejipura.",
    instruction: "Look at the CENTER map: the red pulsing corridor is blocked, and the green dashed line avoids the flood.",
  },
  {
    number: 7,
    title: "7. Why It's Smarter: Low-Churn",
    narrative: "Standard algorithms swap en-route units causing chaos and 18-minute delays. Our low-churn solver preserves route continuity, arriving in 4 minutes.",
    instruction: "Click 'Why it's smarter' in the top bar to inspect the live mathematical proof.",
    actionLabel: "Why it's smarter",
  },
  {
    number: 8,
    title: "8. Multi-Layer Security Defenses",
    narrative: "Adversaries try to inject prompt overrides, fake botnet reports, and forged commander keys. All 8 attack vectors are quarantined with 0 false dispatches.",
    instruction: "Click 'Try to attack it' in the top bar to test live simulated attacks.",
    actionLabel: "Try to attack it",
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
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 w-[95%] max-w-6xl bg-[#090b1c]/95 border border-cyan-500/40 rounded-2xl p-3.5 shadow-[0_12px_40px_rgba(0,0,0,0.85)] backdrop-blur-xl z-30 flex items-center justify-between gap-4 select-none">
      {/* Step Badge & Plain Text Explanation */}
      <div className="flex items-center gap-3.5 min-w-0 flex-1">
        <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/60 flex items-center justify-center text-cyan-300 font-mono font-bold text-sm shadow-[0_0_15px_rgba(6,182,212,0.3)] shrink-0">
          {stepData.number}/8
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-wider">
              {stepData.title}
            </span>
            <span className="text-slate-500 text-[10px] hidden sm:inline">•</span>
            <span className="text-[11px] text-slate-300 font-medium truncate hidden sm:inline">
              {stepData.instruction}
            </span>
          </div>
          <p className="text-xs text-slate-100 mt-0.5 leading-snug font-medium line-clamp-2">
            &ldquo;{stepData.narrative}&rdquo;
          </p>
        </div>
      </div>

      {/* Interactive Action & Navigation Buttons */}
      <div className="flex items-center gap-2.5 shrink-0 font-sans">
        {stepData.actionLabel && onActionClick && (
          <button
            onClick={() => onActionClick(currentStep)}
            className="px-3.5 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs font-mono transition-all shadow-[0_0_12px_rgba(6,182,212,0.4)] flex items-center gap-1.5 cursor-pointer shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{stepData.actionLabel}</span>
          </button>
        )}

        <div className="flex items-center gap-1 bg-slate-900 border border-slate-700/80 p-1 rounded-xl">
          <button
            onClick={handlePrev}
            disabled={currentStep <= 1}
            className="px-2.5 py-1 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors flex items-center gap-1 text-xs font-medium font-mono"
            title="Previous Step"
          >
            <ChevronLeft className="w-4 h-4" />
            <span className="hidden md:inline">Back</span>
          </button>
          <button
            onClick={handleNext}
            disabled={currentStep >= DEMO_STEPS.length}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white disabled:opacity-30 transition-colors flex items-center gap-1 text-xs font-semibold font-mono"
            title="Next Step"
          >
            <span>Next</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
