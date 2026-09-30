"""Road Network & Impact Engine for Bengaluru Crisis Response.

Models the road network across major flood hotspots (Silk Board, Bellandur, Koramangala,
ORR Underpass, Marathahalli, HSR Layout), computes shortest reachable paths and travel times,
handles flood road blockages, and checks hospital reachability.
"""
from __future__ import annotations
import math
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
from backend.app.models.resource import Hospital
from backend.app.engines.verification import haversine_distance_km

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
GRAPH_CACHE_FILE = DATA_DIR / "bengaluru_graph.pkl"

# Key Ground Truth Landmarks in South-East Bengaluru (Demo Region)
BENGALURU_HOTSPOTS = {
    "silk_board": {"name": "Central Silk Board Junction", "lat": 12.9176, "lon": 77.6238},
    "hsr_sector_6": {"name": "HSR Layout Sector 6", "lat": 12.9116, "lon": 77.6388},
    "koramangala_4th": {"name": "Koramangala 4th Block", "lat": 12.9345, "lon": 77.6265},
    "bellandur_ecospace": {"name": "Bellandur EcoSpace ORR", "lat": 12.9260, "lon": 77.6762},
    "orr_underpass": {"name": "Outer Ring Road Underpass", "lat": 12.9310, "lon": 77.6850},
    "marathahalli": {"name": "Marathahalli Bridge", "lat": 12.9591, "lon": 77.6974},
    "st_johns_hosp": {"name": "St. John's Medical College Hospital", "lat": 12.9312, "lon": 77.6202},
    "sakra_hosp": {"name": "Sakra World Hospital Bellandur", "lat": 12.9285, "lon": 77.6842},
    "manipal_hosp": {"name": "Manipal Hospital Old Airport Rd", "lat": 12.9583, "lon": 77.6485},
}


class RoadGraphEngine:
    """Deterministic Impact Engine managing road network status and routing."""

    def __init__(self, graph: Optional[nx.Graph] = None):
        if graph is not None:
            self.graph = graph
        else:
            self.graph = self._load_or_build_graph()
        self.blocked_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def _load_or_build_graph(self) -> nx.Graph:
        """Load cached graph or build an interconnected arterial road network."""
        if GRAPH_CACHE_FILE.exists():
            try:
                with open(GRAPH_CACHE_FILE, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass

        # Build realistic arterial network for the 9 key nodes + connecting corridors
        g = nx.Graph()
        for node_id, data in BENGALURU_HOTSPOTS.items():
            g.add_node(node_id, name=data["name"], lat=data["lat"], lon=data["lon"])

        # Arterial links with typical urban speeds (30 km/h baseline in flood/traffic)
        corridors = [
            ("silk_board", "hsr_sector_6", 35.0),
            ("silk_board", "koramangala_4th", 30.0),
            ("silk_board", "st_johns_hosp", 25.0),
            ("koramangala_4th", "st_johns_hosp", 25.0),
            ("koramangala_4th", "manipal_hosp", 30.0),
            ("hsr_sector_6", "bellandur_ecospace", 35.0),
            ("bellandur_ecospace", "orr_underpass", 25.0),
            ("bellandur_ecospace", "sakra_hosp", 30.0),
            ("orr_underpass", "sakra_hosp", 20.0),
            ("orr_underpass", "marathahalli", 40.0),
            ("marathahalli", "manipal_hosp", 35.0),
            ("koramangala_4th", "bellandur_ecospace", 30.0),  # Intermediate cross-link
        ]

        for u, v, speed_kmh in corridors:
            lat1, lon1 = g.nodes[u]["lat"], g.nodes[u]["lon"]
            lat2, lon2 = g.nodes[v]["lat"], g.nodes[v]["lon"]
            dist_km = haversine_distance_km(lat1, lon1, lat2, lon2)
            dist_m = dist_km * 1000.0
            free_flow_mins = (dist_km / speed_kmh) * 60.0
            g.add_edge(
                u, v,
                length_m=dist_m,
                speed_kmh=speed_kmh,
                travel_time_mins=free_flow_mins,
                is_blocked=False,
                flood_depth_m=0.0
            )

        # Cache the graph
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(GRAPH_CACHE_FILE, "wb") as f:
                pickle.dump(g, f)
        except Exception:
            pass

        return g

    def get_nearest_node(self, lat: float, lon: float) -> str:
        """Find the nearest road network node to a given GPS coordinate."""
        best_node = None
        best_dist = float("inf")
        for node, data in self.graph.nodes(data=True):
            d = haversine_distance_km(lat, lon, data["lat"], data["lon"])
            if d < best_dist:
                best_dist = d
                best_node = node
        return best_node or "silk_board"

    def block_road(self, u: str, v: str, reason: str = "flooded", flood_depth: float = 1.0) -> bool:
        """Block a specific road segment due to flood or obstruction."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]["is_blocked"] = True
            self.graph[u][v]["flood_depth_m"] = flood_depth
            self.graph[u][v]["block_reason"] = reason
            key = tuple(sorted([u, v]))
            self.blocked_edges[key] = {
                "u": u, "v": v, "reason": reason, "flood_depth_m": flood_depth
            }
            return True
        return False

    def unblock_road(self, u: str, v: str) -> bool:
        """Clear an obstruction and restore road segment."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]["is_blocked"] = False
            self.graph[u][v]["flood_depth_m"] = 0.0
            key = tuple(sorted([u, v]))
            self.blocked_edges.pop(key, None)
            return True
        return False

    def block_area(self, center_lat: float, center_lon: float, radius_km: float = 0.8, reason: str = "area_flooded") -> List[Tuple[str, str]]:
        """Block all road segments passing through a flooded geographic zone."""
        blocked = []
        for u, v, data in self.graph.edges(data=True):
            u_lat, u_lon = self.graph.nodes[u]["lat"], self.graph.nodes[u]["lon"]
            v_lat, v_lon = self.graph.nodes[v]["lat"], self.graph.nodes[v]["lon"]
            mid_lat = (u_lat + v_lat) / 2.0
            mid_lon = (u_lon + v_lon) / 2.0

            if haversine_distance_km(center_lat, center_lon, mid_lat, mid_lon) <= radius_km:
                self.block_road(u, v, reason=reason)
                blocked.append((u, v))
        return blocked

    def compute_travel_time_minutes(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> Tuple[float, List[str]]:
        """Compute shortest travel time (minutes) and path avoiding blocked roads."""
        start_node = self.get_nearest_node(start_lat, start_lon)
        end_node = self.get_nearest_node(end_lat, end_lon)

        if start_node == end_node:
            local_dist_km = haversine_distance_km(start_lat, start_lon, end_lat, end_lon)
            local_time = (local_dist_km / 20.0) * 60.0
            return max(1.0, local_time), [start_node]

        # Create active subgraph without blocked edges
        active_view = nx.subgraph_view(
            self.graph,
            filter_edge=lambda u, v: not self.graph[u][v].get("is_blocked", False)
        )

        try:
            length, path = nx.single_source_dijkstra(
                active_view, source=start_node, target=end_node, weight="travel_time_mins"
            )
            # Add small terminal penalty for exact GPS to node
            start_off = (haversine_distance_km(start_lat, start_lon, self.graph.nodes[start_node]["lat"], self.graph.nodes[start_node]["lon"]) / 25.0) * 60.0
            end_off = (haversine_distance_km(end_lat, end_lon, self.graph.nodes[end_node]["lat"], self.graph.nodes[end_node]["lon"]) / 25.0) * 60.0
            total_time = length + start_off + end_off
            return float(total_time), path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return float("inf"), []

    def find_best_hospital(
        self, incident_lat: float, incident_lon: float, hospitals: List[Hospital]
    ) -> Tuple[Optional[Hospital], float]:
        """Find the fastest reachable hospital with available capacity."""
        best_hosp = None
        min_eta = float("inf")
        for h in hospitals:
            if h.capacity_available <= 0:
                continue
            eta, path = self.compute_travel_time_minutes(incident_lat, incident_lon, h.lat, h.lon)
            if eta < min_eta:
                min_eta = eta
                best_hosp = h
        return best_hosp, min_eta
