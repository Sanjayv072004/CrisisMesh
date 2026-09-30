"""Comprehensive Phase 5 Test Suite: FastAPI REST Endpoints, RBAC, WebSockets & Replay."""
from __future__ import annotations
import json
import time
import pytest
from starlette.testclient import TestClient
from backend.app.api.main import app
from backend.app.api.auth import auth_service
from backend.app.api.state_manager import state_manager
from backend.app.api.websocket import ws_manager
from backend.app.security.rbac import Role
from backend.app.gateway.auth import HMACAuthenticator


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure clean state before each test."""
    state_manager.reset_scenario()
    ws_manager.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def tokens():
    """Generate dev tokens for viewer, operator, and commander."""
    v_token_model = auth_service.authenticate("viewer", "viewer123", Role.VIEWER)
    o_token_model = auth_service.authenticate("operator", "operator123", Role.OPERATOR)
    c_token_model = auth_service.authenticate("commander", "commander123", Role.COMMANDER)

    return {
        "viewer": auth_service.create_token(v_token_model),
        "operator": auth_service.create_token(o_token_model),
        "commander": auth_service.create_token(c_token_model),
    }


# -------------------------------------------------------------------------
# 1. Health & Security Headers Test
# -------------------------------------------------------------------------
def test_health_and_security_headers(client):
    """Verify /health endpoint and defensive HTTP security headers."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "mode" in data

    # Assert security headers
    headers = resp.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-xss-protection"] == "1; mode=block"
    assert "strict-transport-security" in headers
    assert "content-security-policy" in headers


# -------------------------------------------------------------------------
# 2. Authentication & Profile Test
# -------------------------------------------------------------------------
def test_auth_login_and_profile(client):
    """Verify login with dev credentials and /auth/me profile inspection."""
    # 1. Successful login
    login_resp = client.post(
        "/auth/login",
        json={"username": "commander", "password": "commander123", "role": "commander"}
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["role"] == "commander"
    token = login_data["access_token"]
    assert login_data["public_key_hex"] is not None

    # 2. Verify /auth/me
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user_id"] == "commander"
    assert me_data["role"] == "commander"

    # 3. Invalid credentials rejected
    bad_resp = client.post("/auth/login", json={"username": "baduser", "password": "wrong"})
    assert bad_resp.status_code == 401


# -------------------------------------------------------------------------
# 3. RBAC Enforcement Test
# -------------------------------------------------------------------------
def test_rbac_enforcement(client, tokens):
    """Verify strict role boundaries across viewer, operator, and commander."""
    viewer_h = {"Authorization": f"Bearer {tokens['viewer']}"}
    operator_h = {"Authorization": f"Bearer {tokens['operator']}"}

    # 1. Viewer cannot submit report (403 Forbidden)
    rep_payload = {
        "text": "Flood at Silk Board",
        "source_id": "civ_01",
        "lat": 12.917,
        "lon": 77.623,
    }
    resp_viewer_rep = client.post("/reports", json=rep_payload, headers=viewer_h)
    assert resp_viewer_rep.status_code == 403
    assert "not hold required permission" in resp_viewer_rep.json()["error"]["message"]

    # 2. Operator CAN submit report
    resp_op_rep = client.post("/reports", json=rep_payload, headers=operator_h)
    assert resp_op_rep.status_code == 200
    assert resp_op_rep.json()["status"] == "INGESTED"

    # 3. Viewer cannot approve plan (403 Forbidden)
    resp_viewer_app = client.post("/plan/plan_test/approve", json={"auto_sign": True}, headers=viewer_h)
    assert resp_viewer_app.status_code == 403

    # 4. Operator cannot approve plan (403 Forbidden)
    resp_op_app = client.post("/plan/plan_test/approve", json={"auto_sign": True}, headers=operator_h)
    assert resp_op_app.status_code == 403


# -------------------------------------------------------------------------
# 4. Full Flow Through API (Submit -> Approval Required -> Approve -> Dispatched)
# -------------------------------------------------------------------------
def test_full_flow_through_api(client, tokens):
    """Full operational lifecycle via API: Report Ingest -> Plan Formulation -> Commander Ed25519 Approve -> Dispatch."""
    operator_h = {"Authorization": f"Bearer {tokens['operator']}"}
    commander_h = {"Authorization": f"Bearer {tokens['commander']}"}

    # 1. Ingest report as Operator
    rep_resp = client.post(
        "/reports",
        json={
            "text": "Critical water level rise near Bellandur EcoSpace with trapped vehicles!",
            "source_id": "operator_field_01",
            "lat": 12.935,
            "lon": 77.678,
        },
        headers=operator_h,
    )
    assert rep_resp.status_code == 200

    # 2. State pauses at AWAITING_COMMANDER_APPROVAL
    state_resp = client.get("/state", headers=commander_h)
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert state_data["status"] == "AWAITING_COMMANDER_APPROVAL"
    assert state_data["current_plan"] is not None
    plan_id = state_data["current_plan"]["plan_id"]

    # 3. Retrieve current proposed plan
    plan_resp = client.get("/plan/current", headers=commander_h)
    assert plan_resp.status_code == 200
    assert plan_resp.json()["plan_id"] == plan_id

    # 4. Commander cryptographically approves the plan
    approve_resp = client.post(
        f"/plan/{plan_id}/approve",
        json={"auto_sign": True},
        headers=commander_h,
    )
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["status"] == "DISPATCHED"
    assert approve_data["plan_id"] == plan_id

    # 5. Verify state is now DISPATCHED
    final_state = client.get("/state", headers=commander_h).json()
    assert final_state["status"] == "DISPATCHED"


# -------------------------------------------------------------------------
# 5. Forged Commander Approval Rejected Test
# -------------------------------------------------------------------------
def test_forged_approval_rejected(client, tokens):
    """Verify that forged Ed25519 signatures or plan hash mismatches abort dispatch."""
    commander_h = {"Authorization": f"Bearer {tokens['commander']}"}

    # Ingest incident to form plan
    client.post("/scenario/start", headers=commander_h)
    curr_plan = client.get("/plan/current", headers=commander_h).json()
    plan_id = curr_plan["plan_id"]

    # Attempt approval with bogus signature and forged nonce
    bad_approve_resp = client.post(
        f"/plan/{plan_id}/approve",
        json={
            "signature_hex": "deadbeef" * 8,
            "nonce": "forged-nonce-123",
            "timestamp": time.time(),
            "auto_sign": False,
        },
        headers=commander_h,
    )
    assert bad_approve_resp.status_code == 403
    assert "verification failed" in bad_approve_resp.json()["error"]["message"].lower()


# -------------------------------------------------------------------------
# 6. Plan Rejection Triggers Re-Plan Test
# -------------------------------------------------------------------------
def test_plan_rejection_triggers_replan(client, tokens):
    """Commander rejects proposed plan with rationale, triggering constraint re-plan."""
    commander_h = {"Authorization": f"Bearer {tokens['commander']}"}

    client.post("/scenario/start", headers=commander_h)
    curr_plan = client.get("/plan/current", headers=commander_h).json()
    plan_id = curr_plan["plan_id"]

    reject_resp = client.post(
        f"/plan/{plan_id}/reject",
        json={"reason": "Ambulance 1 needed elsewhere for critical dialysis transport"},
        headers=commander_h,
    )
    assert reject_resp.status_code == 200
    reject_data = reject_resp.json()
    assert reject_data["status"] == "RE_PLANNED"
    assert "dialysis" in reject_data["rejection_reason"]


# -------------------------------------------------------------------------
# 7. HMAC Sensor Ingestion Test
# -------------------------------------------------------------------------
def test_sensor_ingestion_hmac(client):
    """Verify HMAC-SHA256 authenticated sensor ingestion and spoof rejection."""
    auth = HMACAuthenticator()
    sensor_id = "sensor_silkboard_01"
    secret = "shared-sensor-secret-key-32bytes!"
    auth.register_source(sensor_id, secret)

    # 1. Valid HMAC signature
    value = 2.45
    sensor_type = "water_level"
    raw_text = f"sensor_id={sensor_id}&value={value}&type={sensor_type}"
    valid_sig = auth.compute_signature(sensor_id, raw_text.encode("utf-8"))

    valid_resp = client.post(
        "/sensors",
        json={
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "lat": 12.917,
            "lon": 77.623,
            "value": value,
            "unit": "meters",
            "flood_threshold": 0.5,
            "signature_hex": valid_sig,
        },
    )
    assert valid_resp.status_code == 200
    assert valid_resp.json()["status"] == "INGESTED"
    assert valid_resp.json()["flood_confirmed"] is True

    # 2. Corrupt / Spoofed signature
    bad_resp = client.post(
        "/sensors",
        json={
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "lat": 12.917,
            "lon": 77.623,
            "value": value,
            "unit": "meters",
            "flood_threshold": 0.5,
            "signature_hex": "bad_sig_1234567890abcdef",
        },
    )
    assert bad_resp.status_code == 401


# -------------------------------------------------------------------------
# 8. Audit Trail & Verification Endpoints Test
# -------------------------------------------------------------------------
def test_audit_endpoints(client, tokens):
    """Verify /audit, /audit/verify, and /security/events endpoints."""
    viewer_h = {"Authorization": f"Bearer {tokens['viewer']}"}

    # 1. GET /audit
    audit_resp = client.get("/audit", headers=viewer_h)
    assert audit_resp.status_code == 200
    assert audit_resp.json()["count"] >= 1

    # 2. GET /audit/verify
    verify_resp = client.get("/audit/verify", headers=viewer_h)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["is_valid"] is True
    assert verify_resp.json()["status"] == "CHAIN_INTEGRITY_VERIFIED"

    # 3. GET /security/events
    sec_resp = client.get("/security/events", headers=viewer_h)
    assert sec_resp.status_code == 200
    assert "events" in sec_resp.json()


# -------------------------------------------------------------------------
# 9. Attack Demonstration Endpoints Test
# -------------------------------------------------------------------------
def test_attack_demonstration_endpoints(client):
    """Verify all 8 live attack defense simulation routes."""
    attacks = [
        ("prompt_injection", "QUARANTINED"),
        ("duplicate_flood", "BLOCKED"),
        ("spoofed_sensor", "BLOCKED"),
        ("forged_approval", "BLOCKED"),
        ("replay_approval", "BLOCKED"),
        ("tamper_audit_copy", "DETECTED"),
        ("viewer_approve", "BLOCKED"),
        ("fake_report", "PROVISIONAL_ISOLATED"),
    ]

    for atk_type, expected_res in attacks:
        resp = client.post(f"/attacks/{atk_type}")
        assert resp.status_code == 200, f"Failed for {atk_type}: {resp.text}"
        data = resp.json()
        assert data["result"] == expected_res
        assert data["mitigating_layer"] is not None


# -------------------------------------------------------------------------
# 10. WebSocket Streaming & Replay After Reconnect Test
# -------------------------------------------------------------------------
def test_websocket_streaming_and_replay(client, tokens):
    """Verify WebSocket real-time event streaming and last_event_id historical replay."""
    token = tokens["viewer"]

    # 1. Connect WebSocket client
    with client.websocket_connect(f"/ws?token={token}") as ws:
        # Broadcast initial test event
        evt1 = ws_manager.emit(event_type="scenario_status", payload={"step": 1})
        received = ws.receive_json()
        assert received["type"] == "scenario_status"
        assert received["payload"]["step"] == 1
        last_id = received["id"]

    # 2. Emit 2 events while client is disconnected
    evt2 = ws_manager.emit(event_type="incident_updated", payload={"step": 2})
    evt3 = ws_manager.emit(event_type="impact_updated", payload={"step": 3})

    # 3. Reconnect with last_event_id replay protocol
    with client.websocket_connect(f"/ws?token={token}&last_event_id={last_id}") as ws2:
        # Client should immediately receive missed events in exact chronological sequence
        replayed1 = ws2.receive_json()
        assert replayed1["type"] == "incident_updated"
        assert replayed1["payload"]["step"] == 2

        replayed2 = ws2.receive_json()
        assert replayed2["type"] == "impact_updated"
        assert replayed2["payload"]["step"] == 3


# -------------------------------------------------------------------------
# 11. Request Size Limit Middleware Test
# -------------------------------------------------------------------------
def test_request_size_limit(client):
    """Verify RequestSizeLimitMiddleware returns 413 for payloads > 1MB."""
    large_payload = "A" * (1024 * 1024 + 100)  # > 1MB
    headers = {"Content-Length": str(len(large_payload))}
    resp = client.post("/reports", content=large_payload, headers=headers)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
