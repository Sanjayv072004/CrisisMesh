"use client";

import React, { useEffect, useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import {
  Radio,
  Clock,
  RotateCcw,
  ShieldAlert,
  BarChart3,
  Sliders,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
} from "lucide-react";

interface TopBarProps {
  onNextStep?: () => void;
}

export function TopBar({ onNextStep }: TopBarProps) {
  const {
    status,
    scenarioClock,
    connectionStatus,
    auditStatus,
    setSnapshot,
    setAuditStatus,
    toggleAttackPanel,
    toggleUSPPanel,
    isUnderTheHood,
    toggleUnderTheHood,
    currentPlan,
    incidents,
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

  const handleNextAction = async () => {
    if (onNextStep) {
      onNextStep();
      return;
    }
    setIsActing(true);
    try {
      if (Object.keys(incidents).length === 0) {
        const snap = await api.startScenario();
        setSnapshot(snap);
      } else if (status === "AWAITING_COMMANDER_APPROVAL" && currentPlan) {
        await api.approvePlan(currentPlan.plan_id, { auto_sign: true });
        const snap = await api.getStateSnapshot();
        setSnapshot(snap);
      } else if (status === "DISPATCHED" && !incidents["inc_t10_critical_underpass"]) {
        const snap = await api.stepScenario();
        setSnapshot(snap);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsActing(false);
    }
  };

  return (
    <header className="h-14 bg-[#080a18] border-b border-slate-800/80 flex items-center justify-between px-4 select-none z-30 font-sans">
      {/* 1. Left: Brand & Demo Mode Badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-red-950/80 border border-red-700/60 flex items-center justify-center text-red-400 shadow-[0_0_12px_rgba(239,68,68,0.3)]">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wider uppercase text-white font-mono">
                CRISISMESH
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-semibold">
                Demo mode: offline AI
              </span>
            </div>
            <div className="text-[10px] text-slate-400">Bengaluru Flood Command</div>
          </div>
        </div>

        {/* Small Status Pill */}
        <div className="hidden lg:flex items-center gap-1.5 ml-2 font-mono text-xs">
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide border ${
              status === "DISPATCHED"
                ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/60"
                : status === "AWAITING_COMMANDER_APPROVAL"
                ? "bg-amber-950/80 text-amber-300 border-amber-600/60 animate-pulse"
                : "bg-slate-900 text-slate-400 border-slate-800"
            }`}
          >
            {status === "AWAITING_COMMANDER_APPROVAL" ? "Awaiting Approval" : status}
          </span>
        </div>
      </div>

      {/* 2. Center: Quick Exploration Action Buttons */}
      <div className="flex items-center gap-2">
        {/* Button: Try to attack it */}
        <button
          onClick={toggleAttackPanel}
          className="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-red-300 border border-red-800/50 text-xs font-medium font-mono flex items-center gap-1.5 transition-all shadow-sm"
          title="Simulate prompt injections, fake reports, and botnet attacks"
        >
          <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          <span>Try to attack it</span>
        </button>

        {/* Button: Why it's smarter */}
        <button
          onClick={toggleUSPPanel}
          className="px-3 py-1.5 rounded-lg bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-800/50 text-xs font-medium font-mono flex items-center gap-1.5 transition-all shadow-sm"
          title="View live mathematical CP-SAT proof comparing Low-Churn vs Naive re-planning"
        >
          <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
          <span>Why it&apos;s smarter</span>
        </button>

        {/* Toggle: Under the hood */}
        <button
          onClick={toggleUnderTheHood}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium font-mono flex items-center gap-1.5 transition-all border ${
            isUnderTheHood
              ? "bg-violet-950/80 text-violet-300 border-violet-700/80 shadow-[0_0_12px_rgba(139,92,246,0.3)]"
              : "bg-slate-900/60 text-slate-400 hover:text-slate-200 border-slate-800"
          }`}
          title="Toggle technical agent trace, solver costs, and security feeds"
        >
          <Sliders className="w-3.5 h-3.5 text-violet-400" />
          <span>Under the hood</span>
          <span
            className={`w-2 h-2 rounded-full ${
              isUnderTheHood ? "bg-violet-400 animate-pulse" : "bg-slate-600"
            }`}
          />
        </button>
      </div>

      {/* 3. Right: Clock, Telemetry & Next Step CTA */}
      <div className="flex items-center gap-3 font-mono text-xs">
        {/* Time & Connectivity */}
        <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#0b0d1e] border border-slate-800 text-[11px] text-slate-300">
          <Clock className="w-3 h-3 text-slate-400" />
          <span>{timeStr || "00:00:00"} IST</span>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-400 font-bold">{scenarioClock}</span>
          <span className="text-slate-600">|</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
            <span>CONNECTED</span>
          </span>
        </div>

        {/* Small Reset Button */}
        <button
          onClick={handleReset}
          disabled={isActing}
          title="Reset to initial clean scenario"
          className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors disabled:opacity-50"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Primary CTA: Next Step */}
        <button
          onClick={handleNextAction}
          disabled={isActing}
          className="py-1.5 px-3.5 rounded-lg bg-ops-lime hover:bg-[#b5e228] text-[#0b0c1f] font-bold text-xs font-mono uppercase tracking-wider transition-all duration-150 shadow-[0_0_15px_rgba(198,244,50,0.3)] hover:shadow-[0_0_20px_rgba(198,244,50,0.5)] flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <span>Next step</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
}
