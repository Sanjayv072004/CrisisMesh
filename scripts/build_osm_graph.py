"""Generate and cache simplified South-East Bengaluru OSM Road Graph for CrisisMesh."""
from pathlib import Path
import networkx as nx

def generate_bengaluru_osm_graph():
    G = nx.Graph()

    # Hotspot landmark hubs covering South-East Bengaluru
    HUBS = {
        "silk_board": {"name": "Silk Board Junction", "lat": 12.9176, "lon": 77.6238},
        "hsr_layout": {"name": "HSR Layout Sector 6", "lat": 12.9116, "lon": 77.6388},
        "koramangala": {"name": "Koramangala 4th Block", "lat": 12.9345, "lon": 77.6265},
        "bellandur": {"name": "Bellandur EcoSpace", "lat": 12.9260, "lon": 77.6762},
        "orr_underpass": {"name": "Outer Ring Road Underpass", "lat": 12.9310, "lon": 77.6850},
        "marathahalli": {"name": "Marathahalli Bridge", "lat": 12.9591, "lon": 77.6974},
        "hosp_st_johns": {"name": "St. John's Hospital", "lat": 12.9312, "lon": 77.6202},
        "hosp_sakra": {"name": "Sakra World Hospital", "lat": 12.9285, "lon": 77.6842},
        "hosp_manipal": {"name": "Manipal Hospital HAL", "lat": 12.9583, "lon": 77.6485},
        "sarjapur_road": {"name": "Sarjapur Main Road", "lat": 12.9180, "lon": 77.6600},
        "ejipura_flyover": {"name": "Ejipura Flyover Junction", "lat": 12.9400, "lon": 77.6280},
        "domlur_junction": {"name": "Domlur Flyover", "lat": 12.9600, "lon": 77.6380},
        "varthur_road": {"name": "Varthur Kodi Junction", "lat": 12.9550, "lon": 77.7100},
        "ibblur_junction": {"name": "Ibblur Lake Junction", "lat": 12.9220, "lon": 77.6680},
        "ecospace_techpark": {"name": "EcoSpace Outer Ring Road", "lat": 12.9270, "lon": 77.6800},
        "kadubeesanahalli": {"name": "Kadubeesanahalli Underpass", "lat": 12.9360, "lon": 77.6920},
        "devarabeesanahalli": {"name": "Devarabeesanahalli Flyover", "lat": 12.9330, "lon": 77.6880}
    }

    for hub_id, d in HUBS.items():
        G.add_node(hub_id, name=d["name"], lat=float(d["lat"]), lon=float(d["lon"]))

    # Core arterial corridors connecting South-East Bengaluru
    CORRIDORS = [
        ("silk_board", "hsr_layout", 2.1, 4.2),
        ("silk_board", "koramangala", 2.3, 4.5),
        ("silk_board", "hosp_st_johns", 1.8, 3.5),
        ("hsr_layout", "ibblur_junction", 3.2, 5.0),
        ("ibblur_junction", "sarjapur_road", 1.5, 3.0),
        ("ibblur_junction", "bellandur", 2.0, 3.5),
        ("bellandur", "ecospace_techpark", 0.8, 1.5),
        ("ecospace_techpark", "orr_underpass", 1.2, 2.0),
        ("orr_underpass", "devarabeesanahalli", 0.9, 1.8),
        ("devarabeesanahalli", "kadubeesanahalli", 1.1, 2.0),
        ("kadubeesanahalli", "marathahalli", 2.8, 5.0),
        ("marathahalli", "varthur_road", 2.5, 4.5),
        ("marathahalli", "hosp_manipal", 4.5, 7.0),
        ("koramangala", "ejipura_flyover", 1.2, 2.5),
        ("ejipura_flyover", "domlur_junction", 2.4, 4.0),
        ("domlur_junction", "hosp_manipal", 1.8, 3.0),
        ("koramangala", "hosp_st_johns", 0.9, 1.8),
        ("koramangala", "ibblur_junction", 3.8, 6.5),
        ("bellandur", "orr_underpass", 1.5, 3.0),
        ("orr_underpass", "hosp_sakra", 0.6, 1.2),
        ("bellandur", "hosp_sakra", 1.4, 2.5),
        ("sarjapur_road", "bellandur", 2.2, 4.0),
    ]

    for u, v, dist, t_time in CORRIDORS:
        G.add_edge(
            u, v,
            length_km=float(dist),
            travel_time_mins=float(t_time),
            flood_depth_m=0.0,
            is_blocked=False
        )

    out_file = Path(__file__).resolve().parent.parent / "data" / "road_graph.graphml"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, out_file)
    print(f"Graph generated: {len(G.nodes)} nodes, {len(G.edges)} edges saved to {out_file}")

if __name__ == "__main__":
    generate_bengaluru_osm_graph()
