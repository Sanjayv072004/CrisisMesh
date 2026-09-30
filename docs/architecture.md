# CrisisMesh — Architecture Reference

> Technical deep-dive for engineers and judges. For setup instructions see [README.md](../README.md).

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Agent Pipeline](#agent-pipeline)
3. [LangGraph Orchestration](#langgraph-orchestration)
4. [CP-SAT Solver](#cp-sat-solver)
5. [Verification Engine](#verification-engine)
6. [Security Gateway](#security-gateway)
7. [API & WebSocket Layer](#api--websocket-layer)
8. [Frontend Architecture](#frontend-architecture)
9. [Data Flow Walkthrough](#data-flow-walkthrough)
10. [Docker & Network Layout](#docker--network-layout)
11. [Key Design Decisions](#key-design-decisions)

---

## System Overview

```
                     ┌─────────────────────────────────────────────┐
                     │            EXTERNAL (public-net)             │
  Browser ──HTTPS──► │  Next.js 14  :3000  │  FastAPI :8000         │
                     └──────────────────┬──────────────────────────┘
                                        │ JWT / WebSocket
                     ┌──────────────────▼──────────────────────────┐
                     │            INTERNAL (internal-net)           │
                     │  LangGraph Orchestrator                      │
                     │  CP-SAT Solver (OR-Tools)                    │
                     │  Verification Engine                         │
                     │  Postgres (audit log)  Redis (sessions)      │
                     └─────────────────────────────────────────────┘
```

- **Solver and audit store never exposed to the internet** — they live on `internal-net` (`internal: true` in compose).
- All containers run non-root (UID 10001), `no-new-privileges`, read-only filesystem.

---

## Agent Pipeline

Seven specialized agents execute in a directed graph:

```
SituationAgent
      │  structured IncidentSummary (validated Pydantic)
      ▼
SupervisorAgent ◄─────────────────── veto loop (max 3)
      │  approved draft plan                      ▲
      ▼                                           │
ResourceGuardian ─── VETO ─────────────────────┘
      │  cleared plan
      ▼
ImpactAgent          ← road network, blocked nodes
      │  impact-annotated plan
      ▼
CommandAgent         ← CP-SAT solution
      │  assignment list
      ▼
CommAgent            ← public advisories
      │
      ▼
SituationAgent (final summary)
      │
      ▼
  StateSnapshot → WebSocket → Dashboard
```

### Agent roles

| Agent | File | Purpose |
|---|---|---|
| `SituationAgent` | `agents/situation.py` | Parses crisis reports, builds `IncidentSummary` |
| `SupervisorAgent` | `agents/supervisor.py` | Manages veto loop; stops at 3 rounds to prevent infinite cycles |
| `ResourceGuardian` | `agents/guardian.py` | Validates plans: no double-bookings, no credibility < 0.3, blocks injections |
| `ImpactAgent` | `agents/impact.py` | NetworkX road graph; marks nodes unreachable when links fail |
| `CommandAgent` | `agents/command.py` | Converts OR-Tools solution to unit assignments |
| `CommAgent` | `agents/comm.py` | Generates public advisories, unit notifications |
| `SituationAgent` (repeat) | (same) | Final human-facing summary |

---

## LangGraph Orchestration

`backend/app/orchestration/graph.py`

### State schema

```python
class CrisisMeshState(TypedDict):
    incidents: List[IncidentRecord]
    current_plan: Optional[Plan]
    previous_approved_plan: Optional[Plan]
    plan_diff: Optional[PlanDiff]
    veto_count: int
    audit_log: List[AuditEntry]
    llm_degraded: bool
    llm_degraded_reason: Optional[str]
```

### Veto cycle

1. `ResourceGuardian` inspects the draft plan.
2. If it issues a `VETO`, `veto_count += 1`. If `veto_count >= 3`, the graph exits with the last valid partial plan.
3. On approval, the plan proceeds to `ImpactAgent` → `CommandAgent`.

### Checkpointing

`MemorySaver` persists state between graph runs. A `resume_from_checkpoint=True` flag allows re-running from any agent step without re-processing all prior agents.

---

## CP-SAT Solver

`backend/app/engines/solver.py`

Uses **Google OR-Tools CP-SAT** to assign rescue units to incidents subject to:

| Constraint | Implementation |
|---|---|
| Each incident covered by exactly 1 unit | `model.AddExactlyOne(assignments[i])` |
| Unit travel time ≤ timeout | `model.Add(travel_time[u][i] <= MAX_ETA)` |
| Unit not double-booked | `model.AddAtMostOne(assignments_for_unit[u])` |
| Uncertainty penalty | Confidence score `c ∈ [0,1]` penalizes low-confidence incidents |

**Low-churn objective** — Computes a `PlanDiff` after each solve. If a unit was already assigned to an incident in the previous plan, its reassignment cost is 0. This minimises unnecessary unit movements.

---

## Verification Engine

`backend/app/models/verification.py`

Implements a **credibility scoring** system:

```
score = (source_diversity × 0.4) + (sensor_confirmation × 0.4) + (recency × 0.2)
```

- `source_diversity`: Number of independent report sources (adjusted for botnet floods using k-independence check)
- `sensor_confirmation`: Whether the nearest IoT sensor confirms the report within its coverage radius
- `recency`: Reports older than `DECAY_WINDOW` (15 min) lose weight

**Thresholds:**
- `score ≥ 0.7` → `CONFIRMED`
- `0.4 ≤ score < 0.7` → `PROVISIONAL`
- `score < 0.4` → `PROVISIONAL_ISOLATED` (blocked from entering plan)
- `score < 0.3` → Guardian quarantine trigger

---

## Security Gateway

`backend/app/gateway/`

### InjectionDetector (`injection_detector.py`)

Every LLM output is passed through:
1. **Schema validation** (`pydantic.BaseModel.model_validate`) — invalid structure → `ValidationError`
2. **Pattern scan** — regex for known injection strings (`ignore previous instructions`, `DAN`, `jailbreak`, `SYSTEM:`, etc.)
3. **Length and entropy checks** — unusually high Shannon entropy → suspicious

Flagged content: `status = PROVISIONAL_ISOLATED`, blocked from entering plan.

### Rate Limiter (`rate_limiter.py`)

Sliding window per `(ip, route)`. Limits:
- `/api/reports` — 30 requests / 60 seconds
- `/api/auth/login` — 5 attempts / 60 seconds
- WebSocket — 1 connection per user

### Auth (`api/auth.py`)

- JWT in memory (not localStorage, no XSS exfiltration)
- Short-lived WebSocket tokens (60s) generated at upgrade time
- HMAC-SHA256 sensor authentication (each sensor has a shared secret)
- Demo mode: `CRISISMESH_DEMO_MODE=true` enables hardcoded demo users; **must be explicitly enabled**

---

## API & WebSocket Layer

`backend/app/api/`

### REST Endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/health` | GET | none | Health check (used by Docker) |
| `/api/auth/login` | POST | none | Username/password → JWT |
| `/api/reports` | POST | JWT | Ingest crisis report |
| `/api/sensor-data` | POST | HMAC | Ingest IoT sensor reading |
| `/api/run` | POST | JWT | Trigger orchestration run |
| `/api/state` | GET | JWT | Current StateSnapshot |
| `/api/audit` | GET | JWT | Audit log entries |
| `/api/attacks/demo` | POST | JWT (demo) | Trigger demo attack vector |

### WebSocket

`/ws/stream` — Upgrades after JWT + short-lived WS token validation. Pushes:
- `state_update` — full StateSnapshot delta
- `agent_trace` — per-agent execution trace
- `alert` — Guardian vetoes, attack detections

---

## Frontend Architecture

`frontend/src/`

### Tech stack

- **Next.js 14** (App Router, RSC + Client Components)
- **Zustand** — global state store (`store/useCrisisStore.ts`)
- **MapLibre GL** — offline map (tiles served locally)
- **WebSocket hook** — custom `useWebSocket.ts` with reconnect

### Key components

| Component | Purpose |
|---|---|
| `AppShell.tsx` | Root layout, keyboard shortcut handler, global WS connection |
| `IncidentCard.tsx` | Per-incident status card with confidence badge |
| `PlanDiffPanel.tsx` | Shows moved/unchanged units with colour coding |
| `AttackPanel.tsx` | Demo attack panel with outcome display |
| `USPProofPanel.tsx` | 3-tab USP evidence viewer |
| `PresenterControls.tsx` | T0/T+10 scenario buttons |

### Security headers

Set in `next.config.mjs`:
- `Content-Security-Policy` — `default-src 'self'`, `connect-src 'self'`, blocks external data
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## Data Flow Walkthrough

### T0 scenario (Start button → plan on screen)

```
1. User presses "1" (keyboard shortcut)
2. PresenterControls dispatches POST /api/run with T0 scenario seed
3. FastAPI calls CrisisMeshOrchestrator.run(incidents)
4. SituationAgent: extracts 3 IncidentRecords from seed data
5. SupervisorAgent: drafts initial plan (no units yet)
6. ResourceGuardian: approves (no conflicts)
7. ImpactAgent: scores road accessibility (Silk Board node reachable)
8. CommandAgent: calls CP-SAT solver → assigns 3 units
9. CommAgent: generates public advisory text
10. StateSnapshot emitted → WebSocket push
11. React receives 'state_update' → Zustand store update
12. IncidentCards + PlanDiffPanel re-render
```

### T+10 replanning

```
1. User presses "2"
2. Backend: marks Bellandur–Silk Board road blocked (ImpactAgent)
3. Solver re-runs with blockage constraint
4. PlanDiff computed: Unit-2 reassigned, Unit-1 and Unit-3 unchanged
5. Low-churn: objective penalises reassignment → only 1 moved
6. Dashboard shows Unit-2 card in orange ("Reassigned")
```

---

## Docker & Network Layout

```yaml
networks:
  public-net:   # bridge, external — frontend ↔ backend
  internal-net: # bridge, internal: true — backend ↔ DB/Redis, NO internet
```

Services:
- `frontend`: connected to `public-net` only
- `backend`: connected to both (gateway role)
- `postgres`, `redis`: `internal-net` only (not reachable from outside)

All containers:
- Non-root user (UID 10001)
- `read_only: true` + `tmpfs: /tmp`
- `security_opt: [no-new-privileges:true]`
- Health checks (`/health` endpoint)

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| LangGraph over raw Python loops | Built-in state management, conditional edges, checkpointing with `MemorySaver` |
| CP-SAT over greedy assignment | Optimal under constraints; provably finds minimum-cost assignment with uncertainty penalty |
| Pydantic schema validation before LLM output enters graph | Prevents prompt-injection payloads from corrupting downstream agents |
| JWT in memory, not localStorage | localStorage is XSS-accessible; memory token survives page reload only via re-auth |
| `CRISISMESH_DEMO_MODE=false` by default | Prevents accidental demo-user exposure in production |
| Low-churn objective function | Minimises unit disruption; operationally critical — crews need not be relocated unnecessarily |
| Veto loop capped at 3 | Prevents livelock; after 3 vetoes, system uses best partial plan rather than spinning |
| Graceful LLM degradation | If LLM provider fails, system falls back to mock provider and shows a banner; never crashes |
