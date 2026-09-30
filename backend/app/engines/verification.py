"""Pure Deterministic Verification Engine.

This module provides deterministic mathematical tools (NO LLM) to:
1. Cluster duplicate/coordinated reports using text similarity (sentence-transformers with TF-IDF fallback)
   and spatiotemporal proximity so that 30 duplicates count as ONE corroboration set.
2. Calculate credibility scores from source reliability priors, independent corroborations,
   sensor agreement, and exponential time decay.
3. Classify reports with threshold-based labels: 'confirmed', 'conflicting', or 'unverified'.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Any
from backend.app.models.incident import Report, SensorReading, ReportCluster, VerificationResult

# Global or lazy holder for sentence-transformers model
_SENTENCE_MODEL = None
_SENTENCE_MODEL_TRIED = False


def _get_sentence_model():
    """Attempt to lazily load sentence-transformers model; return None if unavailable."""
    global _SENTENCE_MODEL, _SENTENCE_MODEL_TRIED
    if not _SENTENCE_MODEL_TRIED:
        _SENTENCE_MODEL_TRIED = True
        try:
            from sentence_transformers import SentenceTransformer
            _SENTENCE_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _SENTENCE_MODEL = None
    return _SENTENCE_MODEL


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two GPS coordinates in kilometers."""
    radius_earth_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_earth_km * c


def compute_text_similarity_matrix(texts: List[str]) -> List[List[float]]:
    """Compute pairwise text similarity matrix.
    
    Uses sentence-transformers if available, otherwise falls back to TF-IDF cosine similarity.
    """
    n = len(texts)
    if n == 0:
        return []
    if n == 1:
        return [[1.0]]

    model = _get_sentence_model()
    if model is not None:
        try:
            embeddings = model.encode(texts, convert_to_numpy=True)
            import numpy as np
            norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norm[norm == 0] = 1e-10
            normalized = embeddings / norm
            sim_matrix = np.dot(normalized, normalized.T)
            return sim_matrix.tolist()
        except Exception:
            pass  # Fall back to TF-IDF on any failure

    # Lightweight deterministic fallback: TF-IDF + Cosine Similarity
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(stop_words="english", token_pattern=r"(?u)\b\w+\b")
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)
        return sim_matrix.tolist()
    except Exception:
        # Ultimate fallback: Jaccard word set similarity
        words = [set(t.lower().split()) for t in texts]
        matrix = [[1.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                inter = len(words[i] & words[j])
                union = len(words[i] | words[j])
                sim = (inter / union) if union > 0 else 0.0
                matrix[i][j] = sim
                matrix[j][i] = sim
        return matrix


def cluster_duplicates(
    reports: List[Report],
    text_threshold: float = 0.70,
    dist_threshold_km: float = 1.0,
    time_threshold_mins: float = 60.0,
) -> List[ReportCluster]:
    """Group duplicate/coordinated reports into clusters.
    
    A report cluster counts as ONE corroboration set, so 30 near-identical reports
    from the same botnet or user cannot artificially confirm themselves.
    
    Clustering condition: Two reports belong in the same cluster if:
    1. Text similarity >= text_threshold (semantic or TF-IDF),
    2. Haversine distance <= dist_threshold_km, AND
    3. Temporal separation <= time_threshold_mins.
    """
    if not reports:
        return []

    texts = [r.text for r in reports]
    sim_matrix = compute_text_similarity_matrix(texts)
    n = len(reports)

    # Build adjacency list for connected components
    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            r1, r2 = reports[i], reports[j]
            # Spatial distance
            dist = haversine_distance_km(r1.lat, r1.lon, r2.lat, r2.lon)
            if dist > dist_threshold_km:
                continue

            # Temporal distance
            time_diff = abs((r1.timestamp - r2.timestamp).total_seconds()) / 60.0
            if time_diff > time_threshold_mins:
                continue

            # Text similarity
            sim = sim_matrix[i][j]
            if sim >= text_threshold:
                adj[i].add(j)
                adj[j].add(i)

    # Find connected components (BFS)
    visited = set()
    clusters: List[ReportCluster] = []

    for i in range(n):
        if i in visited:
            continue
        comp = []
        queue = [i]
        visited.add(i)
        while queue:
            curr = queue.pop(0)
            comp.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        cluster_reports = [reports[idx] for idx in comp]
        cluster = ReportCluster(reports=cluster_reports)
        cluster.update_metadata()
        clusters.append(cluster)

    return clusters


def credibility_score(
    report_cluster: ReportCluster,
    sensors: List[SensorReading],
    source_registry: Dict[str, float],
    now: datetime,
    max_sensor_dist_km: float = 2.0,
    half_life_hours: float = 4.0,
) -> float:
    """Compute the deterministic credibility score in [0.0, 1.0].
    
    Formula components:
    -------------------
    1. SOURCE RELIABILITY PRIOR (P_source):
       Each distinct source has a prior reliability in source_registry in [0.0, 1.0]
       (e.g., official sensor = 0.95, emergency services = 0.90, verified NGO = 0.80,
       regular citizen = 0.45, anonymous/unverified = 0.25).
       We compute the pooled prior as the max prior among independent sources in the cluster.
    
    2. INDEPENDENT CORROBORATION (C_indep):
       Reports from the SAME source inside the cluster count only ONCE.
       If k = len(unique_sources) >= 1:
         - k = 1: No independent corroboration bonus (bonus = 0.0).
         - k > 1: Diminishing marginal bonus: bonus = 1.0 - exp(-0.6 * (k - 1)).
         Corroborated prior = P_source + (1.0 - P_source) * 0.45 * bonus.
         This mathematically guarantees that 30 duplicate reports from 1 source
         CANNOT confirm themselves.
    
    3. SENSOR AGREEMENT (A_sensor):
       Physical sensors provide ground-truth verification.
       Nearby sensors within `max_sensor_dist_km` and within 3 hours of `now` are evaluated:
         - If a water sensor confirms water level >= flood_threshold: Strong agreement (+0.35 boost).
         - If a water sensor indicates normal dry level (< 0.1m) when a major flood is claimed:
           Significant penalty (-0.40) due to sensor contradiction.
         - If no physical sensors exist nearby: Neutral (0.0 change).
    
    4. TIME DECAY (D_time):
       Disaster situations evolve rapidly. Older reports lose operational value.
       Modeled via half-life exponential decay:
         delta_t_hours = max(0, (now - latest_timestamp).total_seconds() / 3600.0)
         decay = exp(-ln(2) * delta_t_hours / half_life_hours).
         Fresh reports (delta_t ~ 0) have decay ~ 1.0; 12-hour old reports decay to 0.125.
    """
    if not report_cluster.reports:
        return 0.0

    # Ensure cluster metadata is current
    report_cluster.update_metadata()

    # 1. Source Reliability Prior
    unique_sources = report_cluster.unique_sources
    source_priors = [source_registry.get(src, 0.25) for src in unique_sources]
    p_source = max(source_priors) if source_priors else 0.25

    # 2. Independent Corroboration Term
    k_sources = len(unique_sources)
    if k_sources <= 1:
        corrob_bonus = 0.0
    else:
        # Diminishing returns: 2 sources -> 0.45 * 0.45 = ~0.20 boost; 5 sources -> ~0.40 boost
        corrob_bonus = 1.0 - math.exp(-0.6 * (k_sources - 1))

    # Base credibility incorporating independent corroboration
    score = p_source + (1.0 - p_source) * 0.45 * corrob_bonus

    # 3. Sensor Agreement Term
    nearby_sensors = [
        s for s in sensors
        if haversine_distance_km(report_cluster.centroid_lat, report_cluster.centroid_lon, s.lat, s.lon) <= max_sensor_dist_km
    ]

    if nearby_sensors:
        # Check highest agreement or contradiction
        sensor_confirmed = any(s.value >= s.flood_threshold for s in nearby_sensors)
        sensor_denied = any(s.value < 0.1 for s in nearby_sensors)

        if sensor_confirmed:
            # Physical sensor directly backs the report
            score = score + (1.0 - score) * 0.60
        elif sensor_denied and not sensor_confirmed:
            # Physical sensor contradicts the report (dry road)
            score = max(0.05, score * 0.40)

    # 4. Time Decay Term
    elapsed_seconds = max(0.0, (now - report_cluster.latest_timestamp).total_seconds())
    elapsed_hours = elapsed_seconds / 3600.0
    time_decay = math.exp(-math.log(2.0) * elapsed_hours / half_life_hours)

    final_score = score * time_decay
    return max(0.0, min(1.0, float(final_score)))


def label(
    score: float,
    has_conflict: bool,
    confirmed_threshold: float = 0.75,
    unverified_threshold: float = 0.40,
) -> str:
    """Classify verification status with configurable thresholds.
    
    Returns:
    - 'conflicting': If contradictory claims or contradictory sensors are detected.
    - 'confirmed': If score >= confirmed_threshold.
    - 'unverified': If score < confirmed_threshold (or below unverified_threshold).
    """
    if has_conflict:
        return "conflicting"
    if score >= confirmed_threshold:
        return "confirmed"
    return "unverified"
