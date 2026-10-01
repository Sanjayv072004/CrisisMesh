"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import {
  MapPin,
  Ambulance,
  Shield,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Crosshair,
  Maximize2,
  Minimize2,
  Sparkles,
} from "lucide-react";

interface RoadNode {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

interface RoadEdge {
  u: string;
  v: string;
  is_blocked: boolean;
  flood_depth_m: number;
  travel_time_mins: number;
  coordinates: [[number, number], [number, number]];
}

interface GraphData {
  nodes: RoadNode[];
  edges: RoadEdge[];
  total_nodes?: number;
  total_edges?: number;
  blocked_count: number;
  graph_source?: string;
}

const DEFAULT_GRAPH: GraphData = {
  nodes: [
    { id: "silk_board", name: "Silk Board Junction", lat: 12.9176, lon: 77.6238 },
    { id: "hsr_layout", name: "HSR Layout Sector 6", lat: 12.9116, lon: 77.6388 },
    { id: "koramangala", name: "Koramangala 4th Block", lat: 12.9345, lon: 77.6265 },
    { id: "bellandur", name: "Bellandur EcoSpace", lat: 12.9260, lon: 77.6762 },
    { id: "orr_underpass", name: "Outer Ring Road Underpass", lat: 12.9310, lon: 77.6850 },
    { id: "marathahalli", name: "Marathahalli Bridge", lat: 12.9591, lon: 77.6974 },
    { id: "hosp_st_johns", name: "St. John's Hospital", lat: 12.9312, lon: 77.6202 },
    { id: "hosp_sakra", name: "Sakra World Hospital", lat: 12.9285, lon: 77.6842 },
    { id: "hosp_manipal", name: "Manipal Hospital HAL", lat: 12.9583, lon: 77.6485 },
    { id: "sarjapur_road", name: "Sarjapur Main Road", lat: 12.9180, lon: 77.6600 },
    { id: "ejipura_flyover", name: "Ejipura Flyover", lat: 12.9400, lon: 77.6280 },
    { id: "domlur_junction", name: "Domlur Flyover", lat: 12.9600, lon: 77.6380 },
    { id: "varthur_road", name: "Varthur Kodi", lat: 12.9550, lon: 77.7100 },
    { id: "ibblur_junction", name: "Ibblur Lake Junction", lat: 12.9220, lon: 77.6680 },
    { id: "ecospace_techpark", name: "EcoSpace Outer Ring Road", lat: 12.9270, lon: 77.6800 },
    { id: "kadubeesanahalli", name: "Kadubeesanahalli Underpass", lat: 12.9360, lon: 77.6920 },
    { id: "devarabeesanahalli", name: "Devarabeesanahalli Flyover", lat: 12.9330, lon: 77.6880 }
  ],
  edges: [
    { u: "silk_board", v: "hsr_layout", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.2, coordinates: [[77.6238, 12.9176], [77.6388, 12.9116]] },
    { u: "silk_board", v: "koramangala", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.5, coordinates: [[77.6238, 12.9176], [77.6265, 12.9345]] },
    { u: "silk_board", v: "hosp_st_johns", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.5, coordinates: [[77.6238, 12.9176], [77.6202, 12.9312]] },
    { u: "hsr_layout", v: "ibblur_junction", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 5.0, coordinates: [[77.6388, 12.9116], [77.6680, 12.9220]] },
    { u: "ibblur_junction", v: "sarjapur_road", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.0, coordinates: [[77.6680, 12.9220], [77.6600, 12.9180]] },
    { u: "ibblur_junction", v: "bellandur", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.5, coordinates: [[77.6680, 12.9220], [77.6762, 12.9260]] },
    { u: "bellandur", v: "ecospace_techpark", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 1.5, coordinates: [[77.6762, 12.9260], [77.6800, 12.9270]] },
    { u: "ecospace_techpark", v: "orr_underpass", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 2.0, coordinates: [[77.6800, 12.9270], [77.6850, 12.9310]] },
    { u: "orr_underpass", v: "devarabeesanahalli", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 1.8, coordinates: [[77.6850, 12.9310], [77.6880, 12.9330]] },
    { u: "devarabeesanahalli", v: "kadubeesanahalli", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 2.0, coordinates: [[77.6880, 12.9330], [77.6920, 12.9360]] },
    { u: "kadubeesanahalli", v: "marathahalli", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 5.0, coordinates: [[77.6920, 12.9360], [77.6974, 12.9591]] },
    { u: "marathahalli", v: "varthur_road", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.5, coordinates: [[77.6974, 12.9591], [77.7100, 12.9550]] },
    { u: "marathahalli", v: "hosp_manipal", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 7.0, coordinates: [[77.6974, 12.9591], [77.6485, 12.9583]] },
    { u: "koramangala", v: "ejipura_flyover", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 2.5, coordinates: [[77.6265, 12.9345], [77.6280, 12.9400]] },
    { u: "ejipura_flyover", v: "domlur_junction", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.0, coordinates: [[77.6280, 12.9400], [77.6380, 12.9600]] },
    { u: "domlur_junction", v: "hosp_manipal", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.0, coordinates: [[77.6380, 12.9600], [77.6485, 12.9583]] },
    { u: "koramangala", v: "hosp_st_johns", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 1.8, coordinates: [[77.6265, 12.9345], [77.6202, 12.9312]] },
    { u: "koramangala", v: "ibblur_junction", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 6.5, coordinates: [[77.6265, 12.9345], [77.6680, 12.9220]] },
    { u: "bellandur", v: "orr_underpass", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.0, coordinates: [[77.6762, 12.9260], [77.6850, 12.9310]] },
    { u: "orr_underpass", v: "hosp_sakra", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 1.2, coordinates: [[77.6850, 12.9310], [77.6842, 12.9285]] },
    { u: "bellandur", v: "hosp_sakra", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 2.5, coordinates: [[77.6762, 12.9260], [77.6842, 12.9285]] },
    { u: "sarjapur_road", v: "bellandur", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.0, coordinates: [[77.6600, 12.9180], [77.6762, 12.9260]] },
  ],
  blocked_count: 0,
};

export function BengaluruTacticalMap() {
  const {
    incidents,
    units,
    currentPlan,
    selectedIncidentId,
    selectedUnitId,
    setSelectedIncident,
    setSelectedUnit,
  } = useCrisisStore();

  const [graphData, setGraphData] = useState<GraphData>(DEFAULT_GRAPH);

  // Fetch road network graph from backend
  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const data = await api.getRoadGraph();
        if (data && data.nodes && data.nodes.length > 0) {
          setGraphData(data as any);
        }
      } catch (e) {
        // Fallback pre-set
      }
    };
    fetchGraph();
    const interval = setInterval(fetchGraph, 2000);
    return () => clearInterval(interval);
  }, []);

  // Map coordinate bounds for South-East Bengaluru corridor
  const minLat = 12.905;
  const maxLat = 12.975;
  const minLon = 77.610;
  const maxLon = 77.720;

  const project = (lat: number, lon: number): [number, number] => {
    const x = ((lon - minLon) / (maxLon - minLon)) * 88 + 6;
    const y = (1 - (lat - minLat) / (maxLat - minLat)) * 84 + 8;
    return [Math.max(4, Math.min(96, x)), Math.max(4, Math.min(96, y))];
  };

  const incidentList = useMemo(() => {
    return Object.values(incidents).filter(
      (inc) => inc.credibility_score === undefined || inc.credibility_score >= 0.15
    );
  }, [incidents]);

  return (
    <div className="relative w-full h-full bg-[#070814] overflow-hidden flex flex-col select-none">
      {/* Tactical Map Header Bar */}
      <div className="h-9 px-3.5 border-b border-ops-border bg-ops-surface/80 backdrop-blur-md flex items-center justify-between z-20">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-ops-lime animate-pulse" />
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider font-sans">
            Bengaluru South-East Corridor
          </span>
          <span className="text-[10px] text-slate-400 font-mono">
            [12.91°N - 12.97°N, 77.61°E - 77.72°E]
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-slate-900/90 border border-ops-borderBright text-ops-lime font-bold shadow-sm">
            Simplified road network
          </div>
        </div>
      </div>

      {/* SVG Vector Tactical Map Canvas */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center p-2 bg-[#070814]">
        {/* Subtle coordinate grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(139,92,246,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(139,92,246,0.06)_1px,transparent_1px)] bg-[size:5%_7%] pointer-events-none" />

        <svg
          viewBox="0 0 100 100"
          className="w-full h-full max-w-full max-h-full transition-transform duration-300"
          preserveAspectRatio="none"
        >
          <defs>
            {/* Flood ripple glow filter */}
            <filter id="flood-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            {/* Dispatch line gradient */}
            <linearGradient id="dispatch-glow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#C6F432" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#06B6D4" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          {/* 1. Road Graph Network Edges */}
          {graphData?.edges.map((edge, idx) => {
            const [p1, p2] = edge.coordinates;
            const [x1, y1] = project(p1[1], p1[0]);
            const [x2, y2] = project(p2[1], p2[0]);

            return (
              <g key={`edge-${edge.u}-${edge.v}-${idx}`}>
                {/* Outer Road Base Line */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={edge.is_blocked ? "#ef4444" : "#1E1F3D"}
                  strokeWidth={edge.is_blocked ? "2.2" : "1.2"}
                  strokeLinecap="round"
                  filter={edge.is_blocked ? "url(#flood-glow)" : undefined}
                />
                {/* Core Highway Line */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={edge.is_blocked ? "#f87171" : "#4338CA"}
                  strokeWidth={edge.is_blocked ? "1.0" : "0.5"}
                  strokeDasharray={edge.is_blocked ? "1.5,1.5" : "none"}
                  strokeOpacity={edge.is_blocked ? "1" : "0.7"}
                />
                {/* Flooded Road Pulsing Warning Indicator */}
                {edge.is_blocked && (
                  <circle
                    cx={(x1 + x2) / 2}
                    cy={(y1 + y2) / 2}
                    r="1.8"
                    fill="#ef4444"
                    className="animate-ping"
                    opacity="0.8"
                  />
                )}
              </g>
            );
          })}

          {/* 2. Active Plan Animated Dispatch Flow Lines */}
          {currentPlan?.assignments?.map((a) => {
            const unit = units.find((u) => u.id === a.unit_id);
            const inc = incidents[a.incident_id];
            if (!unit || !inc) return null;

            const [ux, uy] = project(unit.lat, unit.lon);
            const [ix, iy] = project(inc.lat, inc.lon);

            return (
              <g key={`dispatch-${a.unit_id}-${a.incident_id}`}>
                {/* Glowing dispatch route background */}
                <line
                  x1={ux}
                  y1={uy}
                  x2={ix}
                  y2={iy}
                  stroke="url(#dispatch-glow)"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeDasharray="2,2"
                  className="animate-pulse"
                  opacity="0.85"
                />
              </g>
            );
          })}

          {/* 3. Road Hub Nodes (Labels for 6 primary areas only) */}
          {graphData?.nodes.map((node) => {
            const [nx, ny] = project(node.lat, node.lon);
            const PRIMARY_AREAS: Record<string, string> = {
              silk_board: "Silk Board",
              koramangala: "Koramangala",
              hsr_layout: "HSR Layout",
              bellandur: "Bellandur",
              orr_underpass: "ORR Underpass",
              marathahalli: "Marathahalli",
            };
            const areaLabel = PRIMARY_AREAS[node.id];

            return (
              <g key={`node-${node.id}`}>
                <circle
                  cx={nx}
                  cy={ny}
                  r={areaLabel ? "1.4" : "0.7"}
                  fill={areaLabel ? "#6366F1" : "#312E81"}
                  stroke="#070814"
                  strokeWidth="0.4"
                />
                {/* Clean Area Label with Background Pill */}
                {areaLabel && (
                  <>
                    <rect
                      x={nx + 1.8}
                      y={ny - 2.5}
                      width={areaLabel.length * 1.05 + 2.5}
                      height="3.4"
                      rx="0.8"
                      fill="#0B0C1F"
                      stroke="#23264E"
                      strokeWidth="0.25"
                      opacity="0.92"
                    />
                    <text
                      x={nx + 2.8}
                      y={ny - 0.2}
                      fill="#E2E8F0"
                      fontSize="2.3"
                      fontFamily="sans-serif"
                      fontWeight="600"
                      textAnchor="start"
                    >
                      {areaLabel}
                    </text>
                  </>
                )}
              </g>
            );
          })}

          {/* 4. Active Incident Markers with Verification Shapes */}
          {incidentList.map((inc) => {
            const [ix, iy] = project(inc.lat, inc.lon);
            const labelUpper = String(inc.verification_label || "").toUpperCase();
            const isConfirmed = labelUpper === "CONFIRMED";
            const isSelected = selectedIncidentId === inc.id;

            return (
              <g
                key={`inc-marker-${inc.id}`}
                onClick={() => setSelectedIncident(inc.id)}
                className="cursor-pointer"
              >
                {/* Outer radar ping */}
                <circle
                  cx={ix}
                  cy={iy}
                  r="4.5"
                  fill="none"
                  stroke={isConfirmed ? "#10B981" : "#F59E0B"}
                  strokeWidth="0.4"
                  className="animate-ping"
                  opacity="0.6"
                />

                {/* Verification-specific Shape */}
                {isConfirmed ? (
                  // Confirmed: Circular Emerald Marker with Inner Check
                  <g>
                    <circle
                      cx={ix}
                      cy={iy}
                      r={isSelected ? "3.6" : "3.0"}
                      fill="#064E3B"
                      stroke="#10B981"
                      strokeWidth={isSelected ? "0.8" : "0.5"}
                    />
                    <circle cx={ix} cy={iy} r="1.2" fill="#10B981" />
                  </g>
                ) : (
                  // Unverified: Amber Warning Diamond Shape
                  <polygon
                    points={`${ix},${iy - 3.2} ${ix + 3.2},${iy} ${ix},${iy + 3.2} ${ix - 3.2},${iy}`}
                    fill="#78350F"
                    stroke="#F59E0B"
                    strokeWidth={isSelected ? "0.8" : "0.5"}
                    strokeDasharray="1,1"
                  />
                )}

                {/* Severity Badge */}
                <text
                  x={ix}
                  y={iy + 0.8}
                  fill="#ffffff"
                  fontSize="2.2"
                  fontWeight="bold"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  {inc.severity}
                </text>
              </g>
            );
          })}

          {/* 5. Emergency Units Fleet Tokens */}
          {units.map((u) => {
            const [ux, uy] = project(u.lat, u.lon);
            const isAmbulance = u.unit_type === "ambulance";
            const isSelected = selectedUnitId === u.id;

            return (
              <g
                key={`unit-marker-${u.id}`}
                onClick={() => setSelectedUnit(u.id)}
                className="cursor-pointer"
              >
                <circle
                  cx={ux}
                  cy={uy}
                  r={isSelected ? "2.6" : "2.2"}
                  fill={isAmbulance ? "#0369A1" : "#047857"}
                  stroke={isAmbulance ? "#38BDF8" : "#34D399"}
                  strokeWidth={isSelected ? "0.7" : "0.4"}
                />
                <text
                  x={ux}
                  y={uy + 0.6}
                  fill="#ffffff"
                  fontSize="1.6"
                  fontWeight="bold"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  {isAmbulance ? `A${u.id.replace("amb_0", "").replace("amb_", "")}` : `R${u.id.replace("rescue_0", "").replace("rescue_", "")}`}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Tactical Map Corner Legend */}
        <div className="absolute bottom-3 left-3 bg-[#0B0C1F]/90 border border-ops-border rounded-lg p-2.5 backdrop-blur-md shadow-lg font-mono text-[10px] space-y-1.5 z-20">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-300" />
            <span className="text-slate-300">CONFIRMED Incident</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-amber-500 rotate-45 border border-amber-300" />
            <span className="text-slate-300">UNVERIFIED Incident</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-red-500 animate-pulse" />
            <span className="text-red-400 font-bold">Flooded / Blocked Road</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-ops-lime border-b border-cyan-400" />
            <span className="text-ops-lime">Active Dispatch Flow</span>
          </div>
        </div>
      </div>
    </div>
  );
}
