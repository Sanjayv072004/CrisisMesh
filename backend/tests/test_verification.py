"""Tests for Deterministic Verification Engine."""
from datetime import datetime, timezone, timedelta
import pytest
from backend.app.models.incident import Report, SensorReading, ReportCluster
from backend.app.engines.verification import cluster_duplicates, credibility_score, label


def test_thirty_duplicate_reports_stay_unverified():
    """Requirement 1: 30 duplicate reports from one source stay unverified.

    Even if a single user or bot submits 30 copies of the same report,
    they must cluster into ONE corroboration set and yield 0 independent corroboration bonus.
    """
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    source_registry = {"unverified_bot_42": 0.35}

    reports = []
    base_text = "Severe flash flood at Silk Board junction underpass! Water is 3 feet high and rising quickly!"
    for i in range(30):
        reports.append(Report(
            id=f"rep_{i:02d}",
            text=f"{base_text} Urgent help needed! [alert #{i}]",
            source_id="unverified_bot_42",
            timestamp=now - timedelta(minutes=i % 15),
            lat=12.9176 + (i * 0.0001),  # Near Silk Board (~10 meters apart)
            lon=77.6238 + (i * 0.0001),
            claimed_type="flood",
            claimed_severity=4
        ))

    # 1. Clustering must group all 30 reports into exactly ONE cluster
    clusters = cluster_duplicates(reports, text_threshold=0.65, dist_threshold_km=1.0, time_threshold_mins=60.0)
    assert len(clusters) == 1, f"Expected 1 cluster for 30 duplicates, got {len(clusters)}"
    cluster = clusters[0]
    assert len(cluster.reports) == 30
    assert cluster.unique_sources == ["unverified_bot_42"]

    # 2. Credibility calculation must NOT award independent corroboration bonus
    score = credibility_score(cluster, sensors=[], source_registry=source_registry, now=now)
    assert score <= 0.40, f"Expected low score for single-source spam, got {score}"

    # 3. Label must remain unverified
    result_label = label(score, has_conflict=False)
    assert result_label == "unverified", f"Expected 'unverified', got '{result_label}'"


def test_report_matching_water_level_sensor_becomes_confirmed():
    """Requirement 2: A report matching a water-level sensor becomes confirmed.

    A citizen report with a moderate prior (0.45) that agrees with a nearby physical
    water-level sensor reading above its flood threshold is upgraded to 'confirmed'.
    """
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    source_registry = {"citizen_sanjay": 0.45}

    report = Report(
        id="rep_bellandur_01",
        text="Bellandur lake overflow has flooded the main road, depth 1 meter, vehicles stalled",
        source_id="citizen_sanjay",
        timestamp=now - timedelta(minutes=5),
        lat=12.9360,
        lon=77.6650,
        claimed_type="flood",
        claimed_severity=4
    )

    cluster = ReportCluster(reports=[report])
    cluster.update_metadata()

    # Telemetry sensor nearby (0.3 km away) reporting 0.95m water (threshold = 0.5m)
    sensor = SensorReading(
        sensor_id="sensor_bellandur_gauge_03",
        sensor_type="water_level",
        lat=12.9370,
        lon=77.6660,
        timestamp=now - timedelta(minutes=2),
        value=0.95,
        unit="meters",
        flood_threshold=0.5
    )

    score = credibility_score(cluster, sensors=[sensor], source_registry=source_registry, now=now)
    assert score >= 0.75, f"Expected confirmed score >= 0.75 with sensor corroboration, got {score}"

    result_label = label(score, has_conflict=False)
    assert result_label == "confirmed", f"Expected 'confirmed', got '{result_label}'"


def test_old_report_decays():
    """Requirement 3: An old report decays over time.

    A report that was initially verified fresh decays after 12 hours and drops back to unverified.
    """
    t0 = datetime(2026, 9, 30, 8, 0, 0, tzinfo=timezone.utc)
    source_registry = {"ngo_relief_agent": 0.85}

    report = Report(
        id="rep_koramangala_01",
        text="Heavy water logging at Koramangala 4th block",
        source_id="ngo_relief_agent",
        timestamp=t0,
        lat=12.9345,
        lon=77.6265,
        claimed_type="flood",
        claimed_severity=3
    )

    cluster = ReportCluster(reports=[report])
    cluster.update_metadata()

    # Fresh evaluation at t0 + 10 mins
    fresh_score = credibility_score(cluster, sensors=[], source_registry=source_registry, now=t0 + timedelta(minutes=10))
    assert fresh_score >= 0.75
    assert label(fresh_score, has_conflict=False) == "confirmed"

    # Stale evaluation at t0 + 16 hours (4 half-lives)
    stale_now = t0 + timedelta(hours=16)
    stale_score = credibility_score(cluster, sensors=[], source_registry=source_registry, now=stale_now)
    assert stale_score < 0.15, f"Expected severe decay below 0.15, got {stale_score}"
    assert label(stale_score, has_conflict=False) == "unverified"


def test_two_sources_that_contradict_become_conflicting():
    """Requirement 4: Two sources that contradict become conflicting.

    When two conflicting accounts are reported (or a conflict flag is raised),
    the system marks the status as 'conflicting'.
    """
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    score = 0.82  # High credibility score alone is overridden by conflict flag
    result_label = label(score, has_conflict=True)
    assert result_label == "conflicting", f"Expected 'conflicting', got '{result_label}'"


def test_botnet_flood_independence_k_stays_one():
    """Requirement 5: Botnet flood of 30 near-identical reports clusters into 1; k stays 1.

    Two reports count as independent only if source_ids differ AND they are not in
    the same duplicate cluster. A botnet flooding 30 near-identical reports gets clustered into 1,
    k stays 1, and credibility does not climb.
    """
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    source_registry = {"botnet_cluster_alpha": 0.05, "bot_clone_99": 0.05}

    reports = []
    base_text = "Huge tree fallen blocking road near Marathahalli bridge!"
    for i in range(30):
        reports.append(Report(
            id=f"flood_rep_{i}",
            text=base_text if i % 2 == 0 else f"{base_text} Help!",
            source_id="botnet_cluster_alpha" if i % 2 == 0 else "bot_clone_99",
            timestamp=now - timedelta(seconds=i * 10),
            lat=12.9590 + (i * 0.00005),
            lon=77.6970 + (i * 0.00005),
            claimed_type="flood",
            claimed_severity=4
        ))

    # All 30 are spatially/temporally/textually near identical -> 1 cluster
    clusters = cluster_duplicates(reports, text_threshold=0.65, dist_threshold_km=1.0, time_threshold_mins=60.0)
    assert len(clusters) == 1, f"Expected 1 cluster for botnet spam, got {len(clusters)}"

    # Score calculation evaluates independence across clusters: k stays 1
    score = credibility_score(reports, sensors=[], source_registry=source_registry, now=now)
    assert score <= 0.20, f"Expected low credibility score <= 0.20 for botnet flood, got {score}"
    assert label(score, has_conflict=False) == "unverified"


def test_per_sensor_coverage_radius():
    """Requirement 4 & 7: Per-sensor coverage_radius_m.

    Silk Board gauge (800m radius) must corroborate Silk Board accident (~25m away),
    but must NOT corroborate Koramangala (1.88 km away).
    """
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    source_registry = {"unverified_anonymous": 0.25, "citizen_sanjay": 0.55}

    silkboard_sensor = SensorReading(
        sensor_id="gauge_silkboard_01",
        sensor_type="water_level",
        lat=12.9178,
        lon=77.6235,
        timestamp=now,
        value=0.85,
        unit="meters",
        flood_threshold=0.5,
        coverage_radius_m=800.0  # 800m coverage limit
    )

    # Koramangala report ~1.88 km away from Silk Board gauge
    koramangala_rep = Report(
        id="rep_koramangala_04",
        text="Unconfirmed caller reports elderly cardiac patient unable to leave waterlogged home on Koramangala 4th Block.",
        source_id="unverified_anonymous",
        timestamp=now,
        lat=12.9345,
        lon=77.6265,
        claimed_type="medical",
        claimed_severity=4
    )

    score_kora = credibility_score([koramangala_rep], sensors=[silkboard_sensor], source_registry=source_registry, now=now)
    # Koramangala is outside 800m -> sensor must NOT corroborate -> score ~ 0.25 -> unverified
    assert score_kora <= 0.40, f"Koramangala should NOT be corroborated by Silk Board sensor! score={score_kora}"
    assert label(score_kora, has_conflict=False) == "unverified"

    # Silk Board report ~25m away from Silk Board gauge
    silkboard_rep = Report(
        id="rep_silkboard_01",
        text="Multi-vehicle collision in deep puddle near Silk Board flyover descent.",
        source_id="citizen_sanjay",
        timestamp=now,
        lat=12.9176,
        lon=77.6238,
        claimed_type="flood",
        claimed_severity=4
    )

    score_sb = credibility_score([silkboard_rep], sensors=[silkboard_sensor], source_registry=source_registry, now=now)
    # Silk Board is inside 800m -> sensor corroborates -> score >= 0.75 -> confirmed
    assert score_sb >= 0.75, f"Silk Board should be corroborated! score={score_sb}"
    assert label(score_sb, has_conflict=False) == "confirmed"


def test_scenario_t0_verification_pipeline():
    """Requirement 7: Verify complete scenario T0 verification results:
    - Silk Board: CONFIRMED (reports + sensor within coverage)
    - Bellandur: CONFIRMED (report + sensor within coverage)
    - Koramangala: UNVERIFIED (single report, no sensor within coverage)
    """
    import json
    from pathlib import Path
    sc_path = Path(__file__).resolve().parent.parent.parent / "data" / "scenario.json"
    with open(sc_path, "r", encoding="utf-8-sig") as f:
        scenario = json.load(f)

    raw_reports = {r["id"]: r for r in scenario.get("raw_reports", [])}
    source_registry = scenario.get("source_registry", {})
    sensors = [SensorReading(**s) for s in scenario.get("sensors", [])]
    now = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    results = {}
    for inc in scenario["t0_incidents"]:
        inc_reps = [raw_reports[rid] for rid in inc.get("report_ids", []) if rid in raw_reports]
        eng_reps = [
            Report(
                id=r["id"],
                text=r["text"],
                source_id=r["source_id"],
                timestamp=datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
                lat=r["lat"],
                lon=r["lon"]
            )
            for r in inc_reps
        ]
        score = credibility_score(eng_reps, sensors=sensors, source_registry=source_registry, now=now)
        lbl = label(score, has_conflict=False)
        results[inc["id"]] = (score, lbl)

    assert results["inc_t0_01"][1] == "confirmed", f"Silk Board expected confirmed, got {results['inc_t0_01']}"
    assert results["inc_t0_02"][1] == "confirmed", f"Bellandur expected confirmed, got {results['inc_t0_02']}"
    assert results["inc_t0_03"][1] == "unverified", f"Koramangala expected unverified, got {results['inc_t0_03']}"

