"use client";

import React, { useState } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import {
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  FastForward,
  ShieldAlert,
  BarChart3,
  Minimize2,
  Maximize2,
  Clock,
  Layers,
} from "lucide-react";

export function PresenterControls() {
  const {
    isPresenterMode,
    togglePresenterMode,
    scenarioClock,
    status,
    playbackSpeed,
    setPlaybackSpeed,
    isPlaying,
    setIsPlaying,
    toggleAttackPanel,
    toggleUSPPanel,
    setSnapshot,
    setAuditStatus,
  } = useCrisisStore();

  const [isBusy, setIsBusy] = useState(false);

  // Deterministic Reset
  const handleReset = async () => {
    setIsBusy(true);
    try {
      const snap = await api.resetScenario();
      setSnapshot(snap);
      const audit = await api.verifyAudit();
      setAuditStatus(audit);
      setIsPlaying(false);
    } catch (e) {
      console.error("Reset failed:", e);
    } finally {
      setIsBusy(false);
    }
  };

  // Start T0
  const handleStartT0 = async () => {
    setIsBusy(true);
    try {
      const snap = await api.startScenario();
      setSnapshot(snap);
    } catch (e) {
      console.error("Start T0 failed:", e);
    } finally {
      setIsBusy(false);
    }
  };

  // Step T+10
  const handleStepT10 = async () => {
    setIsBusy(true);
    try {
      const snap = await api.stepScenario();
      setSnapshot(snap);
    } catch (e) {
      console.error("Step T+10 failed:", e);
    } finally {
      setIsBusy(false);
    }
  };

  // Play / Pause toggle
  const handleTogglePlay = async () => {
    const nextState = !isPlaying;
    setIsPlaying(nextState);
    try {
      await api.playScenario(playbackSpeed);
    } catch (e) {
      console.error("Play failed:", e);
    }
  };

  // Speed selection
  const handleSpeedChange = async (speed: number) => {
    setPlaybackSpeed(speed);
    if (isPlaying) {
      try {
        await api.playScenario(speed);
      } catch (e) {
        console.error("Speed change failed:", e);
      }
    }
  };

  if (!isPresenterMode) {
    return (
      <div className="fixed bottom-3 right-4 z-40">
        <button
          onClick={togglePresenterMode}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600/90 hover:bg-blue-500 text-white font-mono text-xs shadow-lg backdrop-blur border border-blue-400/50 transition-all hover:scale-105"
          title="Press [P] to toggle Presenter Mode"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span>Presenter Mode [P]</span>
        </button>
      </div>
    );
  }

  const isT0Active = scenarioClock === "T+00:00" || status === "AWAITING_COMMANDER_APPROVAL";
  const isT10Active = scenarioClock === "T+10:00" || status === "T10_INJECTED";

  return (
    <div className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-4xl bg-slate-900/95 border border-cyan-500/50 rounded-xl shadow-2xl backdrop-blur-md px-5 py-3 text-slate-100 flex flex-col gap-2.5">
      {/* Top row: Stage Progress Timeline */}
      <div className="flex items-center justify-between gap-4 border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="font-mono text-xs font-bold text-cyan-300">SCENARIO TIMELINE:</span>
        </div>

        <div className="flex-1 flex items-center gap-3 font-mono text-xs">
          {/* T0 Stage */}
          <div
            onClick={handleStartT0}
            className={`flex-1 flex items-center justify-between px-3 py-1.5 rounded-md border cursor-pointer transition-all ${
              isT0Active && !isT10Active
                ? "bg-cyan-950/80 border-cyan-400 text-cyan-200 shadow-inner"
                : "bg-slate-800/60 border-slate-700/80 text-slate-400 hover:border-slate-600"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isT0Active && !isT10Active ? "bg-cyan-400 animate-ping" : "bg-slate-600"}`} />
              <span className="font-bold">Stage 1: T0 Initial Ingestion</span>
            </div>
            <span className="text-[10px] text-cyan-400/80">[1]</span>
          </div>

          {/* Timeline Connector */}
          <span className="text-slate-600 font-bold">&rarr;</span>

          {/* T+10 Stage */}
          <div
            onClick={handleStepT10}
            className={`flex-1 flex items-center justify-between px-3 py-1.5 rounded-md border cursor-pointer transition-all ${
              isT10Active
                ? "bg-amber-950/80 border-amber-400 text-amber-200 shadow-inner"
                : "bg-slate-800/60 border-slate-700/80 text-slate-400 hover:border-slate-600"
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isT10Active ? "bg-amber-400 animate-ping" : "bg-slate-600"}`} />
              <span className="font-bold">Stage 2: T+10 Dynamic Churn</span>
            </div>
            <span className="text-[10px] text-amber-400/80">[2]</span>
          </div>
        </div>

        <button
          onClick={togglePresenterMode}
          className="text-slate-400 hover:text-white p-1 transition-colors"
          title="Minimize Presenter Mode [P]"
        >
          <Minimize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Bottom row: Presenter Actions & Hotkeys */}
      <div className="flex items-center justify-between gap-3 text-xs font-mono">
        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          {/* Reset */}
          <button
            onClick={handleReset}
            disabled={isBusy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 transition-colors disabled:opacity-50"
            title="Deterministic Reset [R]"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset [R]</span>
          </button>

          {/* Play / Pause */}
          <button
            onClick={handleTogglePlay}
            disabled={isBusy}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-bold transition-colors ${
              isPlaying
                ? "bg-amber-600 hover:bg-amber-500 text-white"
                : "bg-cyan-600 hover:bg-cyan-500 text-white"
            }`}
            title="Play / Pause [Space]"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? "Pause [Space]" : "Play [Space]"}</span>
          </button>

          {/* Start T0 */}
          <button
            onClick={handleStartT0}
            disabled={isBusy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-blue-600/80 hover:bg-blue-600 text-white border border-blue-400/50 transition-colors disabled:opacity-50"
            title="Start T0 Ingestion [1]"
          >
            <span>Start T0 [1]</span>
          </button>

          {/* Step T+10 */}
          <button
            onClick={handleStepT10}
            disabled={isBusy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-600/80 hover:bg-amber-600 text-white border border-amber-400/50 transition-colors disabled:opacity-50"
            title="Step T+10 Inundation [2]"
          >
            <SkipForward className="w-3.5 h-3.5" />
            <span>Step T+10 [2]</span>
          </button>
        </div>

        {/* Speed Controls */}
        <div className="flex items-center gap-1 bg-slate-800/80 rounded border border-slate-700 p-0.5">
          <span className="px-2 text-slate-400 text-[11px]">Speed:</span>
          {[0.5, 1.0, 2.0, 5.0].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition-colors ${
                playbackSpeed === s
                  ? "bg-cyan-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Feature Drawers */}
        <div className="flex items-center gap-2">
          {/* Attack Panel Trigger */}
          <button
            onClick={toggleAttackPanel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-950/80 hover:bg-rose-900/90 text-rose-300 border border-rose-500/50 transition-colors shadow-sm"
            title="Toggle Attack Demonstrations [A]"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span className="font-bold">Attacks [A]</span>
          </button>

          {/* USP Proof Trigger */}
          <button
            onClick={toggleUSPPanel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-950/80 hover:bg-indigo-900/90 text-indigo-300 border border-indigo-500/50 transition-colors shadow-sm"
            title="Toggle Live USP Optimization Proof [U]"
          >
            <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-bold">USP Proof [U]</span>
          </button>
        </div>
      </div>
    </div>
  );
}
