"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import { useCrisisStore } from "@/store/useCrisisStore";
import { api } from "@/lib/api";
import { IncidentRecord, Unit } from "@/types";
import {
  MapPin,
  Ambulance,
  Shield,
  Home,
  AlertTriangle,
  Flame,
  CheckCircle2,
  AlertOctagon,
  HelpCircle,
  Maximize2,
  Minimize2,
  Layers,
  Crosshair,
  Navigation,
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
  blocked_count: number;
}

const DEFAULT_GRAPH: GraphData = {
  nodes: [
    { id: "koramangala_junction", name: "Koramangala 80ft Junction", lat: 12.9352, lon: 77.6245 },
    { id: "silk_board", name: "Central Silk Board Junction", lat: 12.9172, lon: 77.6228 },
    { id: "hsr_layout", name: "HSR Layout 27th Main", lat: 12.9116, lon: 77.6433 },
    { id: "bellandur_lake", name: "Bellandur Outer Ring Road", lat: 12.9304, lon: 77.6784 },
    { id: "marathahalli_bridge", name: "Marathahalli Bridge", lat: 12.9569, lon: 77.7011 },
    { id: "whitefield_junction", name: "Whitefield Hope Farm", lat: 12.9698, lon: 77.7499 },
    { id: "domlur_flyover", name: "Domlur Flyover", lat: 12.9609, lon: 77.6387 },
    { id: "sarjapur_road", name: "Sarjapur Fire Hub", lat: 12.9237, lon: 77.6534 },
    { id: "indiranagar_100ft", name: "Indiranagar 100ft Road", lat: 12.9719, lon: 77.6412 },
  ],
  edges: [
    { u: "koramangala_junction", v: "silk_board", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.5, coordinates: [[77.6245, 12.9352], [77.6228, 12.9172]] },
    { u: "silk_board", v: "hsr_layout", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.2, coordinates: [[77.6228, 12.9172], [77.6433, 12.9116]] },
    { u: "hsr_layout", v: "bellandur_lake", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 5.1, coordinates: [[77.6433, 12.9116], [77.6784, 12.9304]] },
    { u: "bellandur_lake", v: "marathahalli_bridge", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 6.0, coordinates: [[77.6784, 12.9304], [77.7011, 12.9569]] },
    { u: "marathahalli_bridge", v: "whitefield_junction", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 8.5, coordinates: [[77.7011, 12.9569], [77.7499, 12.9698]] },
    { u: "koramangala_junction", v: "domlur_flyover", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 5.0, coordinates: [[77.6245, 12.9352], [77.6387, 12.9609]] },
    { u: "domlur_flyover", v: "indiranagar_100ft", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.0, coordinates: [[77.6387, 12.9609], [77.6412, 12.9719]] },
    { u: "hsr_layout", v: "sarjapur_road", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 3.5, coordinates: [[77.6433, 12.9116], [77.6534, 12.9237]] },
    { u: "sarjapur_road", v: "bellandur_lake", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.0, coordinates: [[77.6534, 12.9237], [77.6784, 12.9304]] },
    { u: "domlur_flyover", v: "marathahalli_bridge", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 7.2, coordinates: [[77.6387, 12.9609], [77.7011, 12.9569]] },
    { u: "koramangala_junction", v: "sarjapur_road", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 4.8, coordinates: [[77.6245, 12.9352], [77.6534, 12.9237]] },
    { u: "indiranagar_100ft", v: "marathahalli_bridge", is_blocked: false, flood_depth_m: 0.0, travel_time_mins: 6.8, coordinates: [[77.6412, 12.9719], [77.7011, 12.9569]] },
  ],
  blocked_count: 0,
};

export function BengaluruTacticalMap() {
  const {
    incidents,
    units,
    currentPlan,
    isOfflineMap,
    toggleOfflineMap,
    selectedIncidentId,
    selectedUnitId,
    setSelectedIncident,
    setSelectedUnit,
    status,
  } = useCrisisStore();

  const [graphData, setGraphData] = useState<GraphData>(DEFAULT_GRAPH);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [hoveredItem, setHoveredItem] = useState<{ type: string; id: string; name: string } | null>(null);

  // Fetch road network graph from backend
  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const data = await api.getRoadGraph();
        if (data && data.nodes && data.nodes.length > 0) {
          setGraphData(data as any);
        }
      } catch (e) {
        // Fallback already pre-set
      }
    };
    fetchGraph();
    const interval = setInterval(fetchGraph, 2000);
    return () => clearInterval(interval);
  }, []);

  // Map coordinate bounds for Bengaluru South-East corridor
  // Lat: 12.900 to 12.980 | Lon: 77.610 to 77.760
  const minLat = 12.900;
  const maxLat = 12.980;
  const minLon = 77.610;
  const maxLon = 77.760;

  const project = (lat: number, lon: number): [number, number] => {
    const x = ((lon - minLon) / (maxLon - minLon)) * 92 + 4;
    // Invert Y because latitude goes south-to-north while SVG goes top-to-bottom
    const y = (1 - (lat - minLat) / (maxLat - minLat)) * 88 + 6;
    return [Math.max(4, Math.min(96, x)), Math.max(4, Math.min(96, y))];
  };

  const incidentList = useMemo(() => {
    return Object.values(incidents).filter(
      (inc) => inc.credibility_score === undefined || inc.credibility_score >= 0.15
    );
  }, [incidents]);

  return (
    <div className="relative w-full h-full bg-[#070a12] overflow-hidden flex flex-col select-none">
      {/* Tactical Map Header Bar */}
      <div className="h-9 px-3 border-b border-ops-border bg-ops-surface/80 backdrop-blur flex items-center justify-between z-20">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-ops-emerald animate-pulse" />
          <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Bengaluru South-East Corridor
          </span>
          <span className="text-[10px] text-slate-400 font-mono">
            [12.91°N - 12.98°N, 77.61°E - 77.76°E]
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300">
            TACTICAL VECTOR GRAPH (9 NODES, 12 CORRIDORS)
          </div>
        </div>
      </div>

      {/* SVG Vector Tactical Map Canvas */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center p-2">
        {/* Subtle coordinate grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:4%_6%] pointer-events-none" />

        <svg
          viewBox="0 0 100 100"
          className="w-full h-full max-w-full max-h-full transition-transform duration-300"
          preserveAspectRatio="none"
        >
          {/* 1. Road Graph Network Edges */}
          {graphData?.edges.map((edge, idx) => {
            const [p1, p2] = edge.coordinates;
            const [x1, y1] = project(p1[1], p1[0]);
            const [x2, y2] = project(p2[1], p2[0]);

            return (
              <g key={`edge-${edge.u}-${edge.v}-${idx}`}>
                {/* Outer Road Stroke */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={edge.is_blocked ? "#ef4444" : "#1e293b"}
                  strokeWidth={edge.is_blocked ? "1.8" : "1.2"}
                  strokeLinecap="round"
                  className={edge.is_blocked ? "animate-pulse" : ""}
                />
                {/* Core Road Highway Line */}
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={edge.is_blocked ? "#f87171" : "#0284c7"}
                  strokeWidth={edge.is_blocked ? "0.9" : "0.5"}
                  strokeDasharray={edge.is_blocked ? "1.5,1.5" : "none"}
                  strokeOpacity={edge.is_blocked ? "1" : "0.6"}
                />
                {/* Water Level Blockage Indicator Marker */}
                {edge.is_blocked && (
                  <circle
                    cx={(x1 + x2) / 2}
                    cy={(y1 + y2) / 2}
                    r="1.2"
                    fill="#ef4444"
                    className="animate-ping"
                  />
                )}
              </g>
            );
          })}

          {/* 2. Active Dispatch Lines from Current Plan */}
          {currentPlan?.assignments.map((assignment, idx) => {
            const unit = units.find((u) => u.id === assignment.unit_id);
            const inc = incidents[assignment.incident_id];
            if (!unit || !inc) return null;

            const [ux, uy] = project(unit.lat, unit.lon);
            const [ix, iy] = project(inc.lat, inc.lon);

            return (
              <g key={`dispatch-${assignment.unit_id}-${assignment.incident_id}-${idx}`}>
                {/* Animated Glowing Dispatch Vector */}
                <line
                  x1={ux}
                  y1={uy}
                  x2={ix}
                  y2={iy}
                  stroke={assignment.is_provisional ? "#f59e0b" : "#10b981"}
                  strokeWidth="0.8"
                  strokeDasharray="2,2"
                  strokeLinecap="round"
                  className="animate-[dash_1.5s_linear_infinite]"
                />
              </g>
            );
          })}

          {/* 3. Arterial Junction Nodes */}
          {graphData?.nodes.map((node) => {
            const [nx, ny] = project(node.lat, node.lon);
            return (
              <g
                key={`node-${node.id}`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredItem({ type: "Junction", id: node.id, name: node.name })}
                onMouseLeave={() => setHoveredItem(null)}
              >
                <circle cx={nx} cy={ny} r="1.0" fill="#0f172a" stroke="#0284c7" strokeWidth="0.4" />
                <text
                  x={nx}
                  y={ny + 2.5}
                  fontSize="1.6"
                  textAnchor="middle"
                  fill="#94a3b8"
                  className="font-mono pointer-events-none select-none"
                >
                  {node.name.split(" ")[0]}
                </text>
              </g>
            );
          })}

          {/* 4. Incident Markers (Sized by Severity, Shaped by Verification Label) */}
          {incidentList.map((inc) => {
            const [ix, iy] = project(inc.lat, inc.lon);
            const isSelected = selectedIncidentId === inc.id;
            const size = 1.4 + inc.severity * 0.45; // Sized by severity 1-5

            const isConfirmed = inc.verification_label === "CONFIRMED";
            const isConflicting = inc.verification_label === "CONFLICTING";
            const color = isConfirmed ? "#10b981" : isConflicting ? "#ef4444" : "#f59e0b";

            return (
              <g
                key={`inc-${inc.id}`}
                onClick={() => setSelectedIncident(inc.id)}
                onMouseEnter={() => setHoveredItem({ type: `Incident (SEV ${inc.severity})`, id: inc.id, name: inc.title })}
                onMouseLeave={() => setHoveredItem(null)}
                className="cursor-pointer transition-transform hover:scale-125"
              >
                {/* Selection Halo */}
                {isSelected && (
                  <circle cx={ix} cy={iy} r={size + 2} fill="none" stroke="#38bdf8" strokeWidth="0.6" className="animate-ping" />
                )}

                {/* Shape by Verification Label */}
                {isConfirmed ? (
                  // Confirmed: Circular Beacon
                  <circle
                    cx={ix}
                    cy={iy}
                    r={size}
                    fill={color}
                    stroke="#022c22"
                    strokeWidth="0.5"
                    fillOpacity="0.85"
                  />
                ) : isConflicting ? (
                  // Conflicting: Triangle Warning Shape
                  <polygon
                    points={`${ix},${iy - size * 1.3} ${ix - size * 1.2},${iy + size} ${ix + size * 1.2},${iy + size}`}
                    fill={color}
                    stroke="#450a0a"
                    strokeWidth="0.5"
                    fillOpacity="0.85"
                  />
                ) : (
                  // Unverified: Diamond Shape
                  <polygon
                    points={`${ix},${iy - size * 1.2} ${ix + size * 1.2},${iy} ${ix},${iy + size * 1.2} ${ix - size * 1.2},${iy}`}
                    fill={color}
                    stroke="#451a03"
                    strokeWidth="0.5"
                    fillOpacity="0.85"
                  />
                )}

                {/* Severity Badge Text */}
                <text
                  x={ix}
                  y={iy + 0.4}
                  fontSize="1.4"
                  textAnchor="middle"
                  fill="#000000"
                  fontWeight="bold"
                  className="select-none pointer-events-none font-mono"
                >
                  {inc.severity}
                </text>
              </g>
            );
          })}

          {/* 5. Emergency Fleet Units (Icons by Capability) */}
          {units.map((unit) => {
            const [ux, uy] = project(unit.lat, unit.lon);
            const isSelected = selectedUnitId === unit.id;
            const isEnRoute = unit.status === "en_route";
            const isUnavailable = unit.status === "unavailable";
            const statusColor = isUnavailable ? "#ef4444" : isEnRoute ? "#f59e0b" : "#38bdf8";

            return (
              <g
                key={`unit-${unit.id}`}
                onClick={() => setSelectedUnit(unit.id)}
                onMouseEnter={() => setHoveredItem({ type: `Unit (${unit.unit_type})`, id: unit.id, name: unit.name || unit.id })}
                onMouseLeave={() => setHoveredItem(null)}
                className="cursor-pointer transition-transform hover:scale-125"
              >
                {/* Halo */}
                {isSelected && (
                  <circle cx={ux} cy={uy} r="3.2" fill="none" stroke="#a855f7" strokeWidth="0.6" className="animate-ping" />
                )}

                {/* Unit Node Pin */}
                <rect
                  x={ux - 1.8}
                  y={uy - 1.8}
                  width="3.6"
                  height="3.6"
                  rx="0.8"
                  fill="#090d16"
                  stroke={statusColor}
                  strokeWidth="0.6"
                />

                {/* Unit ID Label */}
                <text
                  x={ux}
                  y={uy + 0.5}
                  fontSize="1.2"
                  textAnchor="middle"
                  fill={statusColor}
                  fontWeight="bold"
                  className="font-mono select-none pointer-events-none uppercase"
                >
                  {unit.id.replace("amb_", "A").replace("rescue_", "R")}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Dynamic Legend / Hover Tooltip */}
        <div className="absolute bottom-3 left-3 bg-ops-surface/90 border border-ops-border rounded-lg p-2.5 backdrop-blur font-mono text-[11px] shadow-2xl z-20 space-y-1.5 max-w-xs">
          <div className="font-bold text-slate-200 border-b border-ops-border pb-1 flex items-center justify-between">
            <span>Tactical Map Legend</span>
            <span className="text-[10px] text-ops-cyan">Auto-Synced</span>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-slate-300">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
              <span>Confirmed Incident</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rotate-45 bg-amber-500 inline-block" />
              <span>Provisional (Unver.)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-red-500 inline-block" />
              <span>Flooded / Blocked</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-cyan-600 inline-block" />
              <span>Clear Road</span>
            </div>
          </div>

          {hoveredItem && (
            <div className="mt-1 pt-1 border-t border-ops-border text-[10px] text-ops-cyan truncate">
              <span className="text-slate-400">{hoveredItem.type}: </span>
              <span className="font-bold text-white">{hoveredItem.name}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
