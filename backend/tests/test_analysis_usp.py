"""Phase 7 USP Proof & Analysis Tests: Mathematical Invariants, Low-Churn & Worst-Case Bounds."""
from __future__ import annotations
import pytest
from starlette.testclient import TestClient
from backend.app.api.main import app
from backend.app.api.state_manager import state_manager


@pytest.fixture(autouse=True)
def reset_state():
    state_manager.reset_scenario()


@pytest.fixture
def client():
    return TestClient(app)


def test_usp_proof_endpoint_and_mathematical_bounds(client):
    """Verify GET /analysis/usp-proof computes live proofs satisfying core algorithmic USPs."""
    resp = client.get("/analysis/usp-proof")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # 1. Verify structure
    assert "low_churn" in data
    assert "uncertainty_aware" in data
    assert "counterfactual" in data

    # 2. USP (a): Low-churn reassignments <= naive reassignments
    lc = data["low_churn"]
    assert lc["low_churn_units_redirected"] <= lc["naive_units_redirected"], (
        f"Low-churn solver redirected {lc['low_churn_units_redirected']} units, "
        f"which must be <= naive ({lc['naive_units_redirected']})"
    )
    assert lc["low_churn_units_redirected"] == 0
    assert lc["naive_units_redirected"] >= 1

    # 3. USP (b): Robust worst-case cost <= naive worst-case cost
    ua = data["uncertainty_aware"]
    assert ua["is_robust_le_naive"] is True
    assert ua["worst_case_robust"] <= ua["worst_case_naive"], (
        f"Robust worst-case cost {ua['worst_case_robust']} must be <= naive {ua['worst_case_naive']}"
    )

    # 4. USP (c): Counterfactual explanation contains runner-up and positive delta cost
    cf = data["counterfactual"]
    assert cf["assigned_unit_id"] != cf["runner_up_unit_id"]
    assert cf["runner_up_eta_minutes"] >= cf["assigned_eta_minutes"]
    assert cf["delta_cost"] >= 0.0
    assert len(cf["rationale"]) > 10
