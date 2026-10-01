"use client";

import React from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { IncidentRecord } from "@/types";
import {
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldCheck,
  Radio,
  MapPin,
  Clock,
  Users,
} from "lucide-react";

interface EmergencyListPanelProps {
  onSelectIncident?: (id: string) => void;
  selectedId?: string | null;
}

export function EmergencyListPanel({ onSelectIncident, selectedId }: EmergencyListPanelProps) {
  const { incidents, setSelectedIncident } = useCrisisStore();

  // Filter out adversarial/quarantined reports from emergency queue (< 0.15 credibility)
  const activeEmergencies = React.useMemo(() => {
    return Object.values(incidents).filter((inc) => {
      if (inc.credibility_score !== undefined && inc.credibility_score < 0.15) {
        return false;
      }
      return true;
    });
  }, [incidents]);

  const handleCardClick = (id: string) => {
    if (onSelectIncident) {
      onSelectIncident(id);
    } else {
      setSelectedIncident(id);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-[#0c0f1d]/80 backdrop-blur-md border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="h-11 px-3.5 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/40 select-none">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Emergencies
          </span>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded-full border border-cyan-800/50">
            {activeEmergencies.length} Active
          </span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">Live Intake</span>
      </div>

      {/* Incident Cards List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {activeEmergencies.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 select-none">
            <Radio className="w-8 h-8 text-slate-700 mb-2 animate-pulse" />
            <p className="text-xs font-semibold text-slate-300">No active emergencies reported.</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
              Incoming 112 calls and flood sensor alerts will appear here in plain language.
            </p>
          </div>
        ) : (
          activeEmergencies.map((inc) => {
            const labelUpper = String(inc.verification_label || "").toUpperCase();
            const isConfirmed = labelUpper === "CONFIRMED";
            const isConflicting = labelUpper === "CONFLICTING";
            const isSelected = selectedId === inc.id;

            // Plain-language confidence & trust
            const credPct = ((inc.credibility_score ?? 0.5) * 100).toFixed(0);

            // Plain urgency label
            let urgencyLabel = "Moderate Priority";
            let urgencyColor = "text-amber-400 bg-amber-950/70 border-amber-800/60";
            if (inc.severity >= 4) {
              urgencyLabel = "Critical Emergency";
              urgencyColor = "text-red-400 bg-red-950/70 border-red-800/60";
            } else if (inc.severity === 3) {
              urgencyLabel = "High Priority";
              urgencyColor = "text-amber-300 bg-amber-950/70 border-amber-800/60";
            }

            return (
              <div
                key={inc.id}
                onClick={() => handleCardClick(inc.id)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer select-none ${
                  isSelected
                    ? "bg-[#161a33] border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.25)] ring-1 ring-cyan-500/50"
                    : "bg-[#101326]/70 hover:bg-[#141830] border-slate-800/90 hover:border-violet-500/40"
                }`}
              >
                {/* Top Row: Title and Urgency */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-xs text-white leading-tight flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="truncate">{inc.title}</span>
                    </div>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full border shrink-0 ${urgencyColor}`}
                  >
                    {urgencyLabel}
                  </span>
                </div>

                {/* Plain English Summary */}
                {inc.description && (
                  <p className="text-[11px] text-slate-300 mt-1.5 line-clamp-2 leading-relaxed">
                    {inc.description}
                  </p>
                )}

                {/* Status Chips & Bayesian Trust */}
                <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between gap-2">
                  {/* Verification Status Chip */}
                  <div className="flex items-center gap-1">
                    {isConfirmed ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/60">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span>Confirmed</span>
                      </span>
                    ) : isConflicting ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-red-950/80 text-red-300 border border-red-700/60">
                        <AlertCircle className="w-3 h-3 text-red-400" />
                        <span>Contradicted</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-amber-950/80 text-amber-300 border border-amber-700/60">
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                        <span>Not yet confirmed</span>
                        <span className="text-[9px] text-amber-400/80 font-mono">(Unverified)</span>
                      </span>
                    )}
                  </div>

                  {/* Trust Percentage */}
                  <span
                    className={`text-[10px] font-mono font-semibold ${
                      isConfirmed ? "text-emerald-400" : "text-amber-400"
                    }`}
                    title="Bayesian posterior credibility from sensor evidence & witness corroboration"
                  >
                    Trust {credPct}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
