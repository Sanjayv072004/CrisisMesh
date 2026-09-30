"""Impact Engine: Road Graph Network, Reachability, Flood Blockages, and Veto Review."""
from __future__ import annotations
import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
from backend.app.models.schemas import Unit, IncidentRecord, Hospital, ImpactReport, Veto
from backend.app.engines.verification import haversine_distance_km

logger = logging.getLogger("CrisisMesh.ImpactEngine")

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
GRAPHML_CACHE_FILE = DATA_DIR / "road_graph.graphml"

# Hotspot nodes covering South-East Bengaluru demo corridor
BENGALURU_NODES = {
    "silk_board": {"name": "Silk Board Junction", "lat": 12.9176, "lon": 77.6238},
    "hsr_layout": {"name": "HSR Layout Sector 6", "lat": 12.9116, "lon": 77.6388},
    "koramangala": {"name": "Koramangala 4th Block", "lat": 12.9345, "lon": 77.6265},
    "bellandur": {"name": "Bellandur EcoSpace", "lat": 12.9260, "lon": 77.6762},
    "orr_underpass": {"name": "Outer Ring Road Underpass", "lat": 12.9310, "lon": 77.6850},
    "marathahalli": {"name": "Marathahalli Bridge", "lat": 12.9591, "lon": 77.6974},
    "hosp_st_johns": {"name": "St. Johns Hospital", "lat": 12.9312, "lon": 77.6202},
    "hosp_sakra": {"name": "Sakra World Hospital", "lat": 12.9285, "lon": 77.6842},
    "hosp_manipal": {"name": "Manipal Hospital HAL", "lat": 12.9583, "lon": 77.6485},
}


class ImpactEngine:
    """Road graph impact analyzer with flood blockage simulation and reachability checks."""

    def __init__(self, force_synthetic: bool = False):
        self.blocked_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        if force_synthetic:
            self.graph = self._build_synthetic_graph()
        else:
            self.graph = self._load_or_create_graph()

    def _load_or_create_graph(self) -> nx.Graph:
        """Load from GraphML cache, attempt OSMnx bounding box, or fallback to synthetic."""
        # 1. Check GraphML cache
        if GRAPHML_CACHE_FILE.exists():
            try:
                g = nx.read_graphml(GRAPHML_CACHE_FILE)
                # Ensure float attributes
                for node, data in g.nodes(data=True):
                    data["lat"] = float(data.get("lat", 12.9))
                    data["lon"] = float(data.get("lon", 77.6))
                for u, v, data in g.edges(data=True):
                    data["travel_time_mins"] = float(data.get("travel_time_mins", 5.0))
                    data["is_blocked"] = str(data.get("is_blocked", "False")).lower() == "true"
                return g
            except Exception as e:
                logger.warning(f"Failed to read graphml cache: {e}. Rebuilding...")

        # 2. Attempt OSMnx download if available
        try:
            import osmnx as ox
            # South-East Bengaluru bounding box (Silk Board to Marathahalli)
            # North, South, East, West
            bbox = (12.9700, 12.9050, 77.7100, 77.6100)
            G_osm = ox.graph_from_bbox(bbox[0], bbox[1], bbox[2], bbox[3], network_type="drive")
            g = nx.Graph(G_osm)
            # Annotate travel times
            for u, v, data in g.edges(data=True):
                length = float(data.get("length", 500.0))
                speed = 30.0  # km/h urban flood traffic
                data["travel_time_mins"] = (length / (speed * 1000.0)) * 60.0
                data["is_blocked"] = False
            self._save_graphml(g)
            return g
        except Exception:
            pass

        # 3. Deterministic synthetic fallback
        g = self._build_synthetic_graph()
        self._save_graphml(g)
        return g

    def _build_synthetic_graph(self) -> nx.Graph:
        """Construct realistic, connected arterial road network across Bengaluru hotspots."""
        g = nx.Graph()
        for node_id, data in BENGALURU_NODES.items():
            g.add_node(node_id, name=data["name"], lat=data["lat"], lon=data["lon"])

        links = [
            ("silk_board", "hsr_layout", 35.0),
            ("silk_board", "koramangala", 30.0),
            ("silk_board", "hosp_st_johns", 25.0),
            ("koramangala", "hosp_st_johns", 25.0),
            ("koramangala", "hosp_manipal", 30.0),
            ("hsr_layout", "bellandur", 35.0),
            ("bellandur", "orr_underpass", 25.0),
            ("bellandur", "hosp_sakra", 30.0),
            ("orr_underpass", "hosp_sakra", 20.0),
            ("orr_underpass", "marathahalli", 40.0),
            ("marathahalli", "hosp_manipal", 35.0),
            ("koramangala", "bellandur", 30.0),
        ]

        for u, v, speed in links:
            lat1, lon1 = g.nodes[u]["lat"], g.nodes[u]["lon"]
            lat2, lon2 = g.nodes[v]["lat"], g.nodes[v]["lon"]
            dist_km = haversine_distance_km(lat1, lon1, lat2, lon2)
            time_mins = (dist_km / speed) * 60.0
            g.add_edge(
                u, v,
                length_m=dist_km * 1000.0,
                speed_kmh=speed,
                travel_time_mins=time_mins,
                is_blocked=False,
                flood_depth_m=0.0
            )
        return g

    def _save_graphml(self, g: nx.Graph) -> None:
        """Serialize graph to GraphML format."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            # Create a copy with string/float safe attrs
            g_export = g.copy()
            for u, v, data in g_export.edges(data=True):
                data["is_blocked"] = str(data.get("is_blocked", False))
            nx.write_graphml(g_export, GRAPHML_CACHE_FILE)
        except Exception as e:
            logger.warning(f"Could not write GraphML cache: {e}")

    def get_nearest_node(self, lat: float, lon: float) -> str:
        """Find the nearest graph node to coordinate."""
        best_node = None
        best_dist = float("inf")
        for node, data in self.graph.nodes(data=True):
            n_lat = float(data.get("lat", 0.0))
            n_lon = float(data.get("lon", 0.0))
            d = haversine_distance_km(lat, lon, n_lat, n_lon)
            if d < best_dist:
                best_dist = d
                best_node = node
        return best_node or "silk_board"

    def block_road(self, u: str, v: str, reason: str = "flooded", flood_depth: float = 1.0) -> bool:
        """Block a road edge in the graph."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]["is_blocked"] = True
            self.graph[u][v]["flood_depth_m"] = flood_depth
            key = tuple(sorted([u, v]))
            self.blocked_edges[key] = {"u": u, "v": v, "reason": reason, "flood_depth": flood_depth}
            return True
        return False

    def unblock_road(self, u: str, v: str) -> bool:
        """Restore a previously blocked road edge."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]["is_blocked"] = False
            key = tuple(sorted([u, v]))
            self.blocked_edges.pop(key, None)
            return True
        return False

    def block_area(self, center_lat: float, center_lon: float, radius_km: float = 0.8, reason: str = "flooded_area") -> List[Tuple[str, str]]:
        """Block all edges traversing within radius of flood epicenter."""
        blocked = []
        for u, v, data in self.graph.edges(data=True):
            lat1, lon1 = float(self.graph.nodes[u]["lat"]), float(self.graph.nodes[u]["lon"])
            lat2, lon2 = float(self.graph.nodes[v]["lat"]), float(self.graph.nodes[v]["lon"])
            mid_lat = (lat1 + lat2) / 2.0
            mid_lon = (lon1 + lon2) / 2.0
            if haversine_distance_km(center_lat, center_lon, mid_lat, mid_lon) <= radius_km:
                self.block_road(u, v, reason=reason)
                blocked.append((u, v))
        return blocked

    def compute_travel_time(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> Tuple[float, List[str]]:
        """Compute shortest travel time (minutes) avoiding blocked roads."""
        start_node = self.get_nearest_node(start_lat, start_lon)
        end_node = self.get_nearest_node(end_lat, end_lon)

        if start_node == end_node:
            local_km = haversine_distance_km(start_lat, start_lon, end_lat, end_lon)
            return max(1.0, (local_km / 20.0) * 60.0), [start_node]

        active_g = nx.subgraph_view(
            self.graph,
            filter_edge=lambda u, v: not self.graph[u][v].get("is_blocked", False)
        )

        try:
            length, path = nx.single_source_dijkstra(active_g, source=start_node, target=end_node, weight="travel_time_mins")
            # Terminal leg GPS off-network approximation
            start_off = (haversine_distance_km(start_lat, start_lon, float(self.graph.nodes[start_node]["lat"]), float(self.graph.nodes[start_node]["lon"])) / 25.0) * 60.0
            end_off = (haversine_distance_km(end_lat, end_lon, float(self.graph.nodes[end_node]["lat"]), float(self.graph.nodes[end_node]["lon"])) / 25.0) * 60.0
            return float(length + start_off + end_off), path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return float("inf"), []

    def travel_time_matrix(
        self, units: List[Unit], targets: List[IncidentRecord]
    ) -> Dict[Tuple[str, str], float]:
        """Compute full matrix of travel times between units and targets."""
        matrix: Dict[Tuple[str, str], float] = {}
        for u in units:
            for t in targets:
                eta, _ = self.compute_travel_time(u.lat, u.lon, t.lat, t.lon)
                matrix[(u.id, t.id)] = round(eta, 1)
        return matrix

    def hard_to_reach(
        self, hospitals: List[Hospital], incidents: List[IncidentRecord], threshold_mins: float = 30.0
    ) -> List[Dict[str, Any]]:
        """Identify incidents with degraded or cut-off hospital connectivity."""
        degraded = []
        for inc in incidents:
            fastest_eta = float("inf")
            best_hosp = None
            for h in hospitals:
                eta, _ = self.compute_travel_time(inc.lat, inc.lon, h.lat, h.lon)
                if eta < fastest_eta:
                    fastest_eta = eta
                    best_hosp = h.id

            if fastest_eta > threshold_mins:
                degraded.append({
                    "incident_id": inc.id,
                    "fastest_hospital": best_hosp,
                    "eta_minutes": fastest_eta if not math.isinf(fastest_eta) else None,
                    "is_unreachable": math.isinf(fastest_eta)
                })
        return degraded

    def review_route(
        self, unit: Unit, incident: IncidentRecord, max_eta_mins: float = 40.0
    ) -> Tuple[bool, float, str]:
        """Review route for potential VETO: returns (is_acceptable, eta, reason)."""
        eta, path = self.compute_travel_time(unit.lat, unit.lon, incident.lat, incident.lon)
        if math.isinf(eta):
            return False, eta, f"Route from unit {unit.id} to incident {incident.id} is completely blocked by flooding"
        if eta > max_eta_mins:
            return False, eta, f"Travel time ({eta:.1f} mins) exceeds critical limit of {max_eta_mins} mins"
        return True, eta, "Route feasible"

    def generate_impact_report(
        self, units: List[Unit], incidents: List[IncidentRecord], hospitals: List[Hospital]
    ) -> ImpactReport:
        """Produce full structured ImpactReport model."""
        matrix = self.travel_time_matrix(units, incidents)
        str_matrix = {f"{u_id}:{t_id}": eta for (u_id, t_id), eta in matrix.items()}

        hard_reach = self.hard_to_reach(hospitals, incidents, threshold_mins=35.0)
        hard_hosp_ids = list({d["fastest_hospital"] for d in hard_reach if d["fastest_hospital"]})

        isolated = [
            inc.id for inc in incidents
            if all(math.isinf(matrix.get((u.id, inc.id), float("inf"))) for u in units)
        ]

        active_g = nx.subgraph_view(
            self.graph,
            filter_edge=lambda u, v: not self.graph[u][v].get("is_blocked", False)
        )
        unreachable_nodes = [node for node, deg in active_g.degree() if deg == 0]

        return ImpactReport(
            flooded_roads=[(u, v) for (u, v) in self.blocked_edges.keys()],
            unreachable_nodes=unreachable_nodes,
            hard_to_reach_hospitals=hard_hosp_ids,
            isolated_incidents=isolated,
            travel_time_matrix=str_matrix
        )
