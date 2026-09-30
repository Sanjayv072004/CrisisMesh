# CrisisMesh API & WebSocket Contract (Phase 5)

This document is the authoritative specification for frontend clients, API integrations, and command room operators interacting with the **CrisisMesh Coordination Control Room API**.

---

## 1. System Architecture & Authentication

### Base URLs
- **HTTP / REST**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/ws`

### Role-Based Access Control (RBAC)
All endpoints enforce cryptographic identity verification and hierarchical roles:
1. `viewer`: Read-only access to state snapshots, active plans, diffs, audit chains, and WebSocket streams.
2. `operator`: Ingests civilian/agency reports, updates unit readiness states, and flags flooded road segments.
3. `commander`: Exclusive authority to cryptographically sign (`Ed25519`), approve, or reject dispatch plans.

### Development Authentication (`POST /auth/login`)
| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `viewer` | `viewer123` | `viewer` | Read-only observation dashboard |
| `operator` | `operator123` | `operator` | Control room report & dispatch ingestion |
| `commander` | `commander123` | `commander` | Incident Commander with bound Ed25519 signing key |

---

## 2. REST Endpoints Specification

### Authentication

#### `POST /auth/login`
- **Role Required**: None (Public)
- **Request Body**:
  ```json
  {
    "username": "commander",
    "password": "commander123",
    "role": "commander"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "role": "commander",
    "user_id": "commander",
    "public_key_hex": "f4cbb88e7ab9a33a...",
    "expires_in_seconds": 86400
  }
  ```

#### `GET /auth/me`
- **Role Required**: `viewer`, `operator`, or `commander`
- **Response** (`200 OK`): Token claims, role, public key, and timestamp validity.

---

### Ingestion & Operations

#### `POST /reports`
- **Role Required**: `operator` or `commander`
- **Security Gates**: Ingestion Gateway (Unicode NFKC, zero-width stripping, HTML escaping, spotlighting delimiters, injection scanner, rate limiter).
- **Request Body**:
  ```json
  {
    "text": "Severe waterlogging near Silk Board junction, 2 cars stranded.",
    "source_id": "citizen_sanjay_42",
    "lat": 12.917,
    "lon": 77.623,
    "ip_address": "127.0.0.1"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "report_id": "rep_citizen_sanjay_42_12917",
    "status": "INGESTED",
    "is_quarantined": false,
    "confidence": 0.8,
    "security_events": []
  }
  ```

#### `POST /sensors`
- **Role Required**: None (HMAC-SHA256 signature required)
- **Request Body**:
  ```json
  {
    "sensor_id": "sensor_silkboard_01",
    "sensor_type": "water_level",
    "lat": 12.917,
    "lon": 77.623,
    "value": 1.45,
    "unit": "meters",
    "flood_threshold": 0.5,
    "signature_hex": "4a7b..."
  }
  ```
- **Response** (`200 OK`): Ingestion confirmation and flood trigger status.

#### `POST /units/{unit_id}/status`
- **Role Required**: `operator` or `commander`
- **Request Body**:
  ```json
  {
    "status": "unavailable",
    "current_target_id": null
  }
  ```
- **Response** (`200 OK`): Triggers selective multi-agent re-plan.

#### `POST /roads/block`
- **Role Required**: `operator` or `commander`
- **Request Body**:
  ```json
  {
    "u": "node_silk_board",
    "v": "node_bellandur",
    "lat": 12.925,
    "lon": 77.635,
    "radius_km": 0.8
  }
  ```
- **Response** (`200 OK`): Updates road reachability and triggers re-plan.

---

### State & Plan Management

#### `GET /state`
- **Role Required**: `viewer`, `operator`, or `commander`
- **Response** (`200 OK`): Complete `StateSnapshot` (incidents, units, hospitals, verification labels, current plan, diffs, briefings, negotiation history).

#### `GET /plan/current`
- **Role Required**: `viewer`, `operator`, or `commander`
- **Response** (`200 OK`): Active or proposed CP-SAT allocation plan.

#### `GET /plan/diff`
- **Role Required**: `viewer`, `operator`, or `commander`
- **Response** (`200 OK`): Plan diff summary, redirect costs, and commander decision flags.

#### `POST /plan/{plan_id}/approve`
- **Role Required**: `commander` exclusively (`CommanderToken`)
- **Request Body**:
  ```json
  {
    "signature_hex": "f137c1758325c459...",
    "nonce": "c62b9a71-6c24-4f51-b0db-b82b992166f2",
    "timestamp": 1727685600.0,
    "auto_sign": true
  }
  ```
- **Action**: Verifies Ed25519 signature, checks nonce freshness, matches canonical plan hash, resumes LangGraph workflow, dispatches fleet.
- **Response** (`200 OK`): `{"status": "DISPATCHED", "plan_id": "...", "nonce": "..."}`.

#### `POST /plan/{plan_id}/reject`
- **Role Required**: `commander` exclusively
- **Request Body**:
  ```json
  {
    "reason": "Ambulance 01 reserved for Silk Board high-priority trauma",
    "forbidden_pairs": [["amb_01", "inc_t0_03"]]
  }
  ```
- **Action**: Injects veto constraint into state and triggers CP-SAT re-solve.

---

### Audit & Security

#### `GET /audit`
- **Response** (`200 OK`): Full append-only cryptographic audit chain.

#### `GET /audit/verify`
- **Response** (`200 OK`):
  ```json
  {
    "is_valid": true,
    "broken_index": null,
    "total_entries": 42,
    "status": "CHAIN_INTEGRITY_VERIFIED"
  }
  ```

#### `GET /security/events`
- **Response** (`200 OK`): Logged security events, injection attempts, and rate-limit violations.

---

### Scenario Control

- `POST /scenario/reset`: Restores scenario to baseline state (`data/scenario.json`).
- `POST /scenario/start`: Starts T0 disaster ingestion and multi-agent plan formulation.
- `POST /scenario/step`: Steps to T+10 change events (ORR submerged SUV, Ambulance 2 failure).
- `POST /scenario/play?speed=1.0`: Executes automated walkthrough with speed control.

---

### Attack Simulations (`POST /attacks/{type}`)

Simulates live attacks to verify defense barriers:
- `fake_report`: Uncorroborated single report $\to$ isolated as provisional.
- `prompt_injection`: Instruction override $\to$ quarantined with confidence $0.05$.
- `duplicate_flood`: 30 rapid duplicate reports in 1s $\to$ HTTP 429 rate limited.
- `spoofed_sensor`: Fake telemetry with invalid HMAC $\to$ perimeter rejected.
- `forged_approval`: Rogue Ed25519 signature $\to$ cryptographic mismatch blocked.
- `replay_approval`: Reusing consumed nonce $\to$ replay store blocked.
- `tamper_audit_copy`: Modifying historical log $\to$ `verify_chain` detects corrupted index.
- `viewer_approve`: Viewer role attempting approval $\to$ privilege escalation blocked.

---

## 3. WebSocket Real-Time Event Stream (`/ws`)

### Connection & Authentication
Connect to `/ws` with the JWT token in query parameters:
```text
ws://localhost:8000/ws?token=<ACCESS_TOKEN>&last_event_id=<LAST_RECEIVED_EVENT_ID>
```

### Historical Replay Protocol (`last_event_id`)
If client reconnects with `last_event_id=evt_000015_a8f9c1`, the server automatically replays all missed events strictly after `last_event_id` in sequence before streaming new events.

### WSEvent JSON Schema
```json
{
  "id": "evt_000023_8b41cd",
  "type": "plan_proposed",
  "timestamp": 1727685600.123,
  "trace_id": "trace-8f7a29bc",
  "payload": { ... }
}
```

### The 11 Typed Event Types

| Event Type | Trigger | Payload Contents |
| :--- | :--- | :--- |
| `agent_message` | Any message sent across `MessageBus` | Full typed `Message` (sender, receiver, type, payload) |
| `incident_updated` | New incident parsed or verification updated | Active incidents dictionary and credibility scores |
| `impact_updated` | Road segment blocked or flood area detected | Blocked roads, cut-off nodes, travel matrix |
| `plan_proposed` | Resource Agent solves CP-SAT allocation | Complete `Plan` (assignments, costs, runner-ups) |
| `plan_diff` | Re-planning delta calculated | Reassigned units, cost delta, decision required |
| `approval_required` | LangGraph pauses at `human_approval` | `plan_id`, `plan_hash`, Commander briefing |
| `plan_approved` | Commander successfully signs approval | `plan_id`, `signature`, `nonce` |
| `dispatch_issued` | Dispatch step executes after approval | `plan_id`, unit dispatch list |
| `security_event` | Injection, spoofing, or rate-limit detected | Structured `SecurityEvent` model |
| `audit_status` | Entry added to hash chain or verified | Hash chain integrity state |
| `scenario_status` | Scenario reset, started, stepped, or played | Action, current status, active thread ID |

---

## 4. Middlewares & Security Invariants

1. **CORS**: Restricted strictly to `http://localhost:3000` (or `FRONTEND_ORIGIN`).
2. **Security Headers**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Content-Security-Policy: default-src 'self'`
3. **Request Size Limit**: Requests with body $> 1\text{ MB}$ return `HTTP 413 Payload Too Large`.
4. **Structured Error Responses**:
   ```json
   {
     "error": {
       "code": "HTTP_403",
       "message": "Access denied: User does not hold required permission 'approve_plan'",
       "details": null
     }
   }
   ```
