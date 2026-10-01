"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { wsClient } from "@/lib/websocket";
import { TopBar } from "./TopBar";
import { PresenterControls } from "../demo/PresenterControls";
import { SafeModeBanner } from "../demo/SafeModeBanner";
import { AttackPanel } from "../demo/AttackPanel";
import { USPProofPanel } from "../demo/USPProofPanel";
import { BengaluruTacticalMap } from "../map/BengaluruTacticalMap";
import { AgentMeshStrip } from "../demo/AgentMeshStrip";
import { SecurityFeed } from "../security/SecurityFeed";
import { GuidedNarrator } from "../demo/GuidedNarrator";
import { HeroIntroModal } from "../demo/HeroIntroModal";
import { DemoSummaryModal } from "../demo/DemoSummaryModal";
import { EmergencyListPanel } from "../emergencies/EmergencyListPanel";
import { RecommendedResponsePanel } from "../response/RecommendedResponsePanel";
import { TechnicalDrawer } from "../drawer/TechnicalDrawer";
import {
  AlertTriangle,
  Ambulance,
  GitBranch,
  Terminal,
  Activity,
  Cpu,
  CheckCircle2,
  Lock,
  Radio,
  FileCheck,
  Shield,
  Layers,
  Flame,
  ShieldAlert,
  Play,
  HelpCircle,
  X,
  Sliders,
} from "lucide-react";

export function AppShell() {
  const {
    incidents,
    units,
    currentPlan,
    planDiff,
    agentTrace,
    status,
    activeRole,
    pendingApproval,
    clearPendingApproval,
    setSnapshot,
    setAuditStatus,
    toggleUSPPanel,
    toggleAttackPanel,
    isUnderTheHood,
  } = useCrisisStore();

  const [leftTab, setLeftTab] = useState<"incidents" | "security">("incidents");
  const [rightTab, setRightTab] = useState<"plan" | "trace">("plan");
  const [isApproving, setIsApproving] = useState(false);
  const [provisionalDecisions, setProvisionalDecisions] = useState<Record<string, boolean>>({});

  // Guided Demo Mode & Modals
  const [showHero, setShowHero] = useState<boolean>(true);
  const [showSummary, setShowSummary] = useState<boolean>(false);
  const [guidedStep, setGuidedStep] = useState<number>(1);
  const [showLegend, setShowLegend] = useState<boolean>(false);

  // Auto-authenticate as Commander on load, connect WebSocket, and fetch state
  useEffect(() => {
    let isMounted = true;
    const initSession = async () => {
      try {
        const auth = await api.demoLogin("commander");
        if (!isMounted) return;
        wsClient.connect(auth.access_token);
        const snap = await api.getStateSnapshot();
        if (isMounted && snap) {
          setSnapshot(snap);
        }
        const audit = await api.verifyAudit();
        if (isMounted && audit) {
          setAuditStatus(audit);
        }
      } catch (e) {
        console.warn("Initial session hydration:", e);
      }
    };
    initSession();
    return () => {
      isMounted = false;
    };
  }, [setSnapshot, setAuditStatus]);

  // Advance Guided Demo automatically based on real backend lifecycle events
  useEffect(() => {
    if (status === "RUNNING_T0" || (Object.keys(incidents).length >= 3 && guidedStep === 1)) {
      setGuidedStep(2);
    }
    if (currentPlan && currentPlan.assignments?.length > 0 && guidedStep === 2) {
      setGuidedStep(3);
    }
    if (status === "AWAITING_COMMANDER_APPROVAL" && guidedStep === 3) {
      setGuidedStep(4);
    }
    if (status === "DISPATCHED" && guidedStep === 4) {
      setGuidedStep(5);
    }
    if (incidents["inc_t10_critical_underpass"] && guidedStep === 5) {
      setGuidedStep(6);
    }
  }, [status, incidents, currentPlan, guidedStep]);

  // Filter out adversarial/quarantined reports from incident queue
  const incidentList = useMemo(() => {
    return Object.values(incidents).filter((inc) => {
      if (inc.credibility_score !== undefined && inc.credibility_score < 0.15) {
        return false; // Quarantined report -> shown in SecurityFeed
      }
      return true;
    });
  }, [incidents]);

  const handleDecisionToggle = (unitId: string) => {
    setProvisionalDecisions((prev) => ({
      ...prev,
      [unitId]: !prev[unitId],
    }));
  };

  const handleApprove = async () => {
    if (!currentPlan) return;
    setIsApproving(true);
    try {
      const res = await api.approvePlan(currentPlan.plan_id, {
        auto_sign: true,
        decisions: provisionalDecisions,
      });
      if (res.status === "DISPATCHED") {
        clearPendingApproval();
        const snap = await api.getStateSnapshot();
        setSnapshot(snap);
        const audit = await api.verifyAudit();
        setAuditStatus(audit);
        if (guidedStep === 4) {
          setGuidedStep(5);
        }
      }
    } catch (e) {
      console.error("Approval failed:", e);
    } finally {
      setIsApproving(false);
    }
  };

  const handleGuidedAction = async (step: number) => {
    try {
      if (step === 1) {
        const snap = await api.startScenario();
        setSnapshot(snap);
        setGuidedStep(2);
      } else if (step === 4) {
        await handleApprove();
      } else if (step === 5) {
        const snap = await api.stepScenario();
        setSnapshot(snap);
        setGuidedStep(6);
      } else if (step === 7) {
        toggleUSPPanel();
      } else if (step === 8) {
        setLeftTab("security");
        setShowSummary(true);
      }
    } catch (e) {
      console.error("Guided action error:", e);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#070a12] text-slate-100 overflow-hidden font-sans antialiased">
      {/* 1. Header & Safe Mode Banner */}
      <TopBar />
      {isUnderTheHood && <SafeModeBanner />}

      {/* 2. Top Slim Agent Mesh Strip (Shown only in Under the Hood mode) */}
      {isUnderTheHood && (
        <div className="px-3 pt-2 shrink-0">
          <AgentMeshStrip />
        </div>
      )}

      {/* 3. Main Tactical 1080p Grid */}
      <main className="flex-1 grid grid-cols-12 gap-2 p-3 min-h-0 pb-20">
        {/* Left Column (3 cols): Emergencies (Full height in Simple View) */}
        <section
          aria-label="Operations Sidebar"
          className={`col-span-3 flex flex-col gap-2 min-h-0 transition-all ${
            guidedStep === 1 || guidedStep === 2
              ? "ring-2 ring-cyan-500 rounded-lg shadow-[0_0_20px_rgba(6,182,212,0.3)]"
              : ""
          }`}
        >
          {/* Incidents Queue / Security Feed */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {leftTab === "security" ? (
              <SecurityFeed />
            ) : (
              <EmergencyListPanel />
            )}
          </div>

          {/* Fleet Readiness Section (Under the Hood only) */}
          {isUnderTheHood && (
            <div className="h-44 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl shrink-0">
              <div className="h-8 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
                <div className="flex items-center gap-2">
                  <Ambulance className="w-3.5 h-3.5 text-ops-cyan" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Fleet Readiness ({units.length})
                  </span>
                </div>
                <span className="text-[10px] font-mono text-ops-muted">Available</span>
              </div>

              <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                {units.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-xs text-ops-muted">
                    No fleet units loaded.
                  </div>
                ) : (
                  units.map((u) => {
                    const typeLabel = (u.unit_type || (u as any).type || "unit").replace("_", " ");
                    return (
                      <div
                        key={u.id}
                        className="flex items-center justify-between py-1 px-2 rounded bg-ops-bg border border-ops-border text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-ops-cyan uppercase font-bold font-mono text-[11px] shrink-0">{u.id}</span>
                          <span className="text-[11px] text-slate-300 capitalize truncate">{typeLabel}</span>
                        </div>
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase shrink-0 whitespace-nowrap leading-none ${
                            u.status === "en_route"
                              ? "bg-amber-950 text-ops-amber border border-amber-800"
                              : u.status === "unavailable"
                              ? "bg-red-950 text-ops-red border border-red-800"
                              : "bg-emerald-950 text-ops-emerald border border-emerald-800"
                          }`}
                        >
                          {u.status}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </section>

        {/* Center Column (5 cols): Dominant Tactical Map Canvas */}
        <section
          aria-label="Bengaluru Tactical Map"
          className={`col-span-5 flex flex-col min-h-0 shadow-2xl rounded-lg overflow-hidden border border-ops-border relative transition-all ${
            guidedStep === 5 || guidedStep === 6
              ? "ring-2 ring-cyan-500 shadow-[0_0_25px_rgba(6,182,212,0.35)]"
              : ""
          }`}
        >
          <BengaluruTacticalMap />

          {/* "What Am I Looking At?" Legend Overlay */}
          {showLegend && (
            <div className="absolute top-11 right-3 w-72 bg-slate-950/95 border border-cyan-500/40 rounded-xl p-3.5 shadow-2xl backdrop-blur-xl z-30 font-mono text-xs select-none">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                <span className="font-bold text-cyan-300">Tactical Command Guide</span>
                <button onClick={() => setShowLegend(false)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-2 text-[11px] text-slate-300">
                <p><span className="text-cyan-400 font-bold">1. Road Network:</span> 9 primary arterial sectors across South-East Bengaluru.</p>
                <p><span className="text-red-400 font-bold">2. Red Segments:</span> Flooded / blocked roads detected by sensors.</p>
                <p><span className="text-amber-400 font-bold">3. Amber Beacons:</span> Unverified reports awaiting confirmation.</p>
                <p><span className="text-emerald-400 font-bold">4. Emerald Beacons:</span> Multi-witness corroborated incidents.</p>
                <p><span className="text-cyan-400 font-bold">5. Dashed Lines:</span> Real-time optimal dispatch routes from CP-SAT solver.</p>
              </div>
            </div>
          )}
        </section>

        {/* Right Column (4 cols): What We Recommend (Full height in Simple View) */}
        <section
          aria-label="Plan and Trace Panels"
          className={`col-span-4 flex flex-col gap-2 min-h-0 transition-all ${
            guidedStep === 3 || guidedStep === 4
              ? "ring-2 ring-cyan-500 rounded-lg shadow-[0_0_20px_rgba(6,182,212,0.3)]"
              : ""
          }`}
        >
          {/* Recommended Response Panel */}
          <RecommendedResponsePanel
            onApproveSuccess={() => {
              if (guidedStep === 4) {
                setGuidedStep(5);
              }
            }}
          />

          {/* Multi-Agent Message Trace (Under the Hood only) */}
          {isUnderTheHood && (
            <div className="h-48 bg-ops-surface border border-ops-border rounded-lg flex flex-col min-h-0 overflow-hidden shadow-xl shrink-0">
              <div className="h-9 border-b border-ops-border px-3 flex items-center justify-between bg-ops-surfaceHover/50 select-none">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-ops-cyan" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Multi-Agent Live Trace ({agentTrace.length})
                  </span>
                </div>
                <span className="text-[10px] font-mono text-ops-emerald flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-ops-emerald animate-ping" />
                  Live Feed
                </span>
              </div>

              <div className="flex-1 overflow-y-auto p-2 space-y-1.5 font-mono text-[11px]">
                {agentTrace.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-ops-muted p-4 text-center select-none">
                    <Terminal className="w-8 h-8 text-slate-700 mb-2" />
                    <p className="text-xs font-semibold text-slate-300">Agent bus quiet.</p>
                    <p className="text-[11px] text-slate-500 mt-1">Inter-agent message payloads stream here.</p>
                  </div>
                ) : (
                  agentTrace.map((msg, idx) => (
                    <div
                      key={`trace-${idx}`}
                      className="p-1.5 rounded bg-ops-bg border border-ops-border flex items-start justify-between gap-2"
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-ops-cyan font-bold shrink-0">{msg.sender}</span>
                        <span className="text-slate-500 shrink-0">&rarr;</span>
                        <span className="text-purple-300 shrink-0">{msg.receiver}</span>
                        <span className="text-slate-400 truncate text-[10px]">[{msg.type}]</span>
                      </div>
                      <span className="text-[9px] text-slate-500 shrink-0">
                        {new Date(msg.timestamp * 1000).toLocaleTimeString([], { hour12: false })}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </section>
      </main>

      {/* 4. Collapsible Bottom Technical Drawer (Shown only in Under the Hood mode) */}
      {isUnderTheHood && <TechnicalDrawer />}

      {/* 5. Guided Demo Bottom Narrator */}
      <GuidedNarrator
        currentStep={guidedStep}
        onStepChange={setGuidedStep}
        onActionClick={handleGuidedAction}
      />

      {/* 5. Drawers & Modals */}
      {showHero && (
        <HeroIntroModal
          onStartDemo={() => {
            setShowHero(false);
            handleGuidedAction(1);
          }}
          onExploreFreely={() => setShowHero(false)}
        />
      )}

      {showSummary && (
        <DemoSummaryModal
          onRestart={() => {
            setShowSummary(false);
            setShowHero(true);
            setGuidedStep(1);
            api.resetScenario().then(setSnapshot);
          }}
          onClose={() => setShowSummary(false)}
        />
      )}

      <AttackPanel />
      <USPProofPanel />
      {isUnderTheHood && <PresenterControls />}
    </div>
  );
}
