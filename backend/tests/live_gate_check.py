"""Phase 5 Gate Check Script.
Runs comprehensive live verification against the running backend server:
- Full API + WebSocket flow (scenario reset/start -> approval_required -> approve -> dispatch_issued)
- RBAC role enforcement (viewer/operator rejected with 403, logged to /security/events)
- Attack endpoints (forged and replayed approvals return BLOCKED with layer & reason)
- Plan rejection and re-plan flow respecting constraints
- WebSocket reconnection replay with last_event_id
- Tamper-evident audit chain verification
- OpenAPI & API Contract documentation files check
"""
import asyncio
import json
import os
import sys
import time
import httpx
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def main():
    print("=" * 70)
    print("      CRISISMESH: PHASE 5 LIVE GATE CHECK & VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Step 0: Check /health
        print("\n[STEP 0] Verifying Backend Health...")
        h_resp = await client.get("/health")
        assert h_resp.status_code == 200, f"Health check failed: {h_resp.text}"
        print(f"  -> Health OK (HTTP 200): {h_resp.json()}")

        # Logins
        print("\n[STEP 1] Authenticating Test Personas...")
        tokens = {}
        for role, creds in [("viewer", "viewer123"), ("operator", "operator123"), ("commander", "commander123")]:
            login_resp = await client.post("/auth/login", json={"username": role, "password": creds})
            assert login_resp.status_code == 200, f"Login failed for {role}: {login_resp.text}"
            tokens[role] = login_resp.json()["access_token"]
            print(f"  -> {role.capitalize()} authenticated successfully.")

        commander_h = {"Authorization": f"Bearer {tokens['commander']}"}
        operator_h = {"Authorization": f"Bearer {tokens['operator']}"}
        viewer_h = {"Authorization": f"Bearer {tokens['viewer']}"}

        # ---------------------------------------------------------------------
        # Gate Item 1: Full Flow Through API + WebSocket
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 1] Full flow through API + WebSocket...")
        ws_uri = f"{WS_URL}?token={tokens['commander']}"
        events_received = []

        async with websockets.connect(ws_uri) as ws:
            print("  -> Connected to WebSocket stream.")

            # Reset scenario
            reset_resp = await client.post("/scenario/reset", headers=commander_h)
            assert reset_resp.status_code == 200

            # Start scenario
            start_resp = await client.post("/scenario/start", headers=commander_h)
            assert start_resp.status_code == 200

            # Collect WS messages until approval_required
            plan_id = None
            plan_hash = None
            for _ in range(25):
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(msg_raw)
                events_received.append(msg["type"])
                print(f"     [WS] Event received: {msg['type']} (id={msg.get('id')})")
                if msg["type"] == "approval_required":
                    plan_id = msg["payload"]["plan_id"]
                    plan_hash = msg["payload"]["plan_hash"]
                    break

            assert plan_id is not None, "Did not receive approval_required event on WS"
            print(f"  -> approval_required received for Plan: {plan_id} (hash: {plan_hash[:16]}...)")

            # Commander approves plan
            approve_resp = await client.post(
                f"/plan/{plan_id}/approve",
                json={"auto_sign": True},
                headers=commander_h,
            )
            assert approve_resp.status_code == 200
            print(f"  -> Plan approved by commander: {approve_resp.json()['status']}")

            # Receive plan_approved and dispatch_issued on WS
            got_dispatch = False
            for _ in range(5):
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(msg_raw)
                events_received.append(msg["type"])
                print(f"     [WS] Event received: {msg['type']} (id={msg.get('id')})")
                if msg["type"] == "dispatch_issued":
                    got_dispatch = True
                    break

            assert got_dispatch, "Did not receive dispatch_issued on WS"
            print("  [CONFIRMED] Full flow succeeded: reset -> start -> approval_required -> approve -> dispatch_issued.")

        # ---------------------------------------------------------------------
        # Gate Item 2: Roles (Viewer & Operator 403 Rejection + Security Events)
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 2] Role Rejections and /security/events logging...")
        # Reset and start to get an unapproved plan
        await client.post("/scenario/reset", headers=commander_h)
        await client.post("/scenario/start", headers=commander_h)
        state_resp = await client.get("/state", headers=commander_h)
        target_plan_id = state_resp.json()["current_plan"]["plan_id"]

        # Viewer attempt
        v_resp = await client.post(f"/plan/{target_plan_id}/approve", json={"auto_sign": True}, headers=viewer_h)
        assert v_resp.status_code == 403, f"Viewer approve should be 403, got {v_resp.status_code}"
        print(f"  -> Viewer approval rejected: HTTP {v_resp.status_code} ({v_resp.json()['error']['code']})")

        # Operator attempt
        o_resp = await client.post(f"/plan/{target_plan_id}/approve", json={"auto_sign": True}, headers=operator_h)
        assert o_resp.status_code == 403, f"Operator approve should be 403, got {o_resp.status_code}"
        print(f"  -> Operator approval rejected: HTTP {o_resp.status_code} ({o_resp.json()['error']['code']})")

        # Check /security/events
        sec_resp = await client.get("/security/events", headers=commander_h)
        assert sec_resp.status_code == 200
        sec_events = sec_resp.json().get("events", [])
        rbac_rejections = [
            e for e in sec_events
            if e["event_type"] in ("rbac_permission_denied", "privilege_escalation_attempt", "unauthorized_dispatch", "rbac_role_denied")
        ]
        assert len(rbac_rejections) >= 2, f"Expected at least 2 RBAC security events, found {len(rbac_rejections)}"
        print(f"  [CONFIRMED] Viewer and operator blocked (HTTP 403); logged in /security/events (found {len(rbac_rejections)} events).")

        # ---------------------------------------------------------------------
        # Gate Item 3: Forged & Replayed Approval Attack Endpoints
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 3] Forged and replayed approval attack endpoints...")
        forged_resp = await client.post("/attacks/forged_approval", headers=commander_h)
        assert forged_resp.status_code == 200
        forged_data = forged_resp.json()
        assert forged_data["result"] == "BLOCKED"
        assert "ApprovalGate" in forged_data["mitigating_layer"]
        assert "failed" in forged_data["detail"].lower() or "signature" in forged_data["detail"].lower()
        print(f"  -> Forged approval: result={forged_data['result']} | layer={forged_data['mitigating_layer']}")
        print(f"     reason: '{forged_data['detail']}'")

        replay_resp = await client.post("/attacks/replay_approval", headers=commander_h)
        assert replay_resp.status_code == 200
        replay_data = replay_resp.json()
        assert replay_data["result"] == "BLOCKED"
        assert "Nonce Replay Store" in replay_data["mitigating_layer"]
        assert "replay" in replay_data["detail"].lower()
        print(f"  -> Replayed approval: result={replay_data['result']} | layer={replay_data['mitigating_layer']}")
        print(f"     reason: '{replay_data['detail']}'")
        print("  [CONFIRMED] Attack endpoints returned 'BLOCKED' with specific layer & reason.")

        # ---------------------------------------------------------------------
        # Gate Item 4: Reject Flow Triggers Re-Plan Respecting Reason
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 4] Reject flow triggers re-plan respecting reason...")
        state_pre = await client.get("/state", headers=commander_h)
        plan_pre_id = state_pre.json()["current_plan"]["plan_id"]
        rejection_reason = "Ambulance 1 assigned unit reserved for ICU transfer"
        forbidden_pairs = [["amb_01", "inc_t0_03"]]

        reject_resp = await client.post(
            f"/plan/{plan_pre_id}/reject",
            json={"reason": rejection_reason, "forbidden_pairs": forbidden_pairs},
            headers=commander_h,
        )
        assert reject_resp.status_code == 200
        reject_data = reject_resp.json()
        assert reject_data["status"] == "RE_PLANNED"
        assert rejection_reason in reject_data["rejection_reason"]
        new_plan_id = reject_data["new_plan_id"]
        assert new_plan_id != plan_pre_id, "New plan ID must differ from rejected plan"

        # Verify new plan does not assign amb_01 to inc_t0_03
        state_post = await client.get("/state", headers=commander_h)
        new_plan = state_post.json()["current_plan"]
        for a in new_plan.get("assignments", []):
            assert not (a["unit_id"] == "amb_01" and a["incident_id"] == "inc_t0_03"), \
                "Re-plan violated forbidden assignment constraint!"

        print(f"  -> Plan {plan_pre_id} rejected; re-plan created new Plan {new_plan_id}.")
        print(f"  -> Verified constraint enforced: amb_01 not assigned to inc_t0_03.")
        print("  [CONFIRMED] Reject flow triggers re-plan and respects commander reason.")

        # ---------------------------------------------------------------------
        # Gate Item 5: WebSocket Reconnection Replay with last_event_id
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 5] WebSocket reconnection replay with last_event_id...")
        checkpoint_id = None
        async with websockets.connect(ws_uri) as ws1:
            print("  -> Connected WS1 to establish event stream...")
            # Trigger report 1 while connected to get a baseline event ID
            await client.post(
                "/reports",
                json={
                    "text": "Baseline flood warning at Silk Board junction",
                    "source_id": "operator_silkboard",
                    "lat": 12.917,
                    "lon": 77.623,
                },
                headers=operator_h,
            )
            # Read event to capture checkpoint
            ev1_raw = await asyncio.wait_for(ws1.recv(), timeout=5.0)
            ev1 = json.loads(ev1_raw)
            checkpoint_id = ev1["id"]
            print(f"  -> Captured checkpoint event: id={checkpoint_id} ({ev1['type']})")

        # Disconnected now! Trigger event 2 while disconnected
        await client.post(
            "/reports",
            json={
                "text": "Water levels rising at HSR Layout sector 3",
                "source_id": "operator_hsr",
                "lat": 12.912,
                "lon": 77.644,
            },
            headers=operator_h,
        )

        # Reconnect with last_event_id
        replay_uri = f"{WS_URL}?token={tokens['commander']}&last_event_id={checkpoint_id}"
        replayed_events = []
        async with websockets.connect(replay_uri) as ws2:
            print(f"  -> Reconnected WS2 with last_event_id={checkpoint_id}...")
            for _ in range(5):
                try:
                    ev_raw = await asyncio.wait_for(ws2.recv(), timeout=2.0)
                    ev = json.loads(ev_raw)
                    replayed_events.append(ev)
                    print(f"     [REPLAY] Received id={ev['id']} ({ev['type']})")
                except asyncio.TimeoutError:
                    break

        assert len(replayed_events) > 0, "No replayed events received after reconnection"
        # Confirm monotonic sequence
        event_ids = [e["id"] for e in replayed_events]
        assert all(event_ids[i] < event_ids[i+1] for i in range(len(event_ids)-1)), "Events out of order!"
        assert all(eid > checkpoint_id for eid in event_ids), "Replayed events must be strictly after checkpoint"
        print(f"  [CONFIRMED] Missed events ({len(replayed_events)}) replayed in strict monotonic order.")

        # ---------------------------------------------------------------------
        # Gate Item 6: Audit Chain Integrity
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 6] Tamper-evident Audit Verification...")
        audit_verify_resp = await client.get("/audit/verify", headers=commander_h)
        assert audit_verify_resp.status_code == 200
        audit_res = audit_verify_resp.json()
        assert audit_res["is_valid"] is True, f"Audit chain verification failed: {audit_res}"
        print(f"  -> Audit chain verification result: is_valid={audit_res['is_valid']}")
        print(f"  -> Blocks verified: {audit_res['total_entries']}")
        print(f"  -> Status: {audit_res['status']}")
        print("  [CONFIRMED] GET /audit/verify returns valid=True after operational run.")

        # ---------------------------------------------------------------------
        # Gate Item 7: Contract Files Committed & Available for Phase 6
        # ---------------------------------------------------------------------
        print("\n[GATE ITEM 7] Checking Contract Files...")
        openapi_path = "docs/openapi.json"
        api_contract_path = "docs/api-contract.md"
        assert os.path.exists(openapi_path), f"Missing {openapi_path}"
        assert os.path.exists(api_contract_path), f"Missing {api_contract_path}"

        with open(openapi_path, "r") as f:
            spec = json.load(f)
            route_count = len(spec.get("paths", {}))
            print(f"  -> {openapi_path}: OK ({route_count} routes specified)")

        with open(api_contract_path, "r") as f:
            content = f.read()
            print(f"  -> {api_contract_path}: OK ({len(content)} characters, {len(content.splitlines())} lines)")

        print("  [CONFIRMED] Contract files exist and are ready for Phase 6 TypeScript generation.")

    print("\n" + "=" * 70)
    print("      ALL PHASE 5 GATE CHECK ITEMS CONFIRMED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
