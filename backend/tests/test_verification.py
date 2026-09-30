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
