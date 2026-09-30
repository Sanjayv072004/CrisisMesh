# CrisisMesh Demo Script -- Phase 7
**Audience:** Judges / Evaluators | **Duration:** <= 4 minutes at 1x speed
**Safe Mode:** ON by default (mock LLM, cached graph, offline map fallback)

---

## Pre-Demo Checklist

`
[ ] Backend running: python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000
    with CRISISMESH_DEMO_MODE=true
[ ] Frontend running: npm run dev (port 3000)
[ ] Browser: http://localhost:3000 -- auto-logged in as Operator (NEXT_PUBLIC_DEMO_AUTOLOGIN=true)
[ ] Safe Mode banner (cyan) visible at top
[ ] Presenter Controls bar visible at bottom (press P to show if minimised)
`

---

## Minute-by-Minute Script

### 0:00 - 0:30 . Opening -- The Problem

Bengaluru EOC receives dozens of conflicting reports during floods.
Dispatchers manually cross-reference -- 5-10 min per incident.
CrisisMesh automates with 7 AI agents + provably safe, uncertainty-aware planning.

- Map (centre): 3 pulsing markers -- Silk Board, Bellandur, Koramangala
- Incidents panel (left): severity badges
- Top bar: AUDIT INTACT, mode badge MOCK (safe mode)

### 0:30 - 1:00 . T0 -- Scenario Start

1. Press S / 1 -- Start T0
2. Agents run: Ingestion -> Situation -> Verification -> Impact -> Allocation
3. Agent Trace scrolls real-time typed bus messages
4. Verification outcomes:
   - CONFIRMED: Silk Board (2 independent reports + traffic sensor)
   - CONFIRMED: Bellandur (water-level sensor match)
   - UNVERIFIED: Koramangala (single source, no sensor)
5. Plan panel: assignments + cost breakdown

### 1:00 - 1:30 . T+10 -- Dynamic Re-plan with Low-Churn

1. Press T / 2 -- Step T+10
2. New critical underpass incident; en-route rescue team closer but mid-mission
3. Plan Diff: before/after highlighted amber, cost-of-change shown
4. lambda=60 (low-churn): keeps en-route unit, dispatches idle unit
5. lambda=0 (naive) would interrupt -- proven in USP panel

### 1:30 - 2:00 . Attack Panel -- Security Under Fire

1. Press A -- Attack Panel opens
2. Fake Report: BLOCKED by IngestionGateway
3. Prompt Injection: BLOCKED by LLMSandbox
4. 30-Report Flood: BLOCKED by RateLimiter
5. Spoofed Sensor: BLOCKED by VerificationAgent
6. Tampered Audit Entry: BLOCKED by AuditChain -- hash chain break detected
7. Agent Trace: attacked entries highlighted rose/red

### 2:00 - 2:45 . USP Proof Panel -- Mathematical Guarantees

1. Press U -- USP Proof Panel opens
2. Tab (a): Low-Churn vs Naive -- units_redirected_low_churn <= units_redirected_naive
3. Tab (b): Uncertainty-Aware -- worst_case_robust <= worst_case_naive (proven)
4. Tab (c): Counterfactual -- optimal vs runner-up with delta ETA and delta cost

### 2:45 - 3:15 . Safe Mode and Role Demo

1. Toggle Safe Mode -- amber LIVE MODE WARNING; toggle back
2. Switch role Operator -> Viewer
3. Attempt approval: 403 Forbidden (viewer cannot approve)
4. Switch back to Operator
5. DevTools -> Application -> Local Storage: empty (JWT in memory only)

### 3:15 - 3:50 . Reset and Repeatability

1. Press R -- Reset to clean T0 (deterministic seed)
2. Select 2x speed, press Space to Play
3. Full scenario plays in ~30s; audit chain remains INTACT

### 3:50 - 4:00 . Close

7 agents, uncertainty-aware CP-SAT planning, cryptographic audit chain,
provable security -- all in under 4 minutes. CrisisMesh.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| P | Toggle Presenter Controls |
| Space | Play / Pause |
| S / 1 | Start T0 |
| T / 2 | Step T+10 |
| R | Reset |
| A | Toggle Attack Panel |
| U | Toggle USP Proof Panel |
| Esc | Close any open panel |

---

## Judge Q&A -- One-Line Answers

Q: Is verification real or rule-based?
A: Real -- VerificationAgent uses source registry, sensor coverage radii, timestamp proximity; no precomputed fields.

Q: How do you prove the low-churn guarantee?
A: CP-SAT solver run twice (lambda=0 naive, lambda=60 low-churn); assert units_redirected_low_churn <= units_redirected_naive. See test_analysis_usp.py.

Q: What if the LLM hallucinates?
A: LLM output is sandboxed, parsed into Pydantic schemas; injection blocked at gateway; all decisions explainable via audit chain.

Q: Is the audit chain tamper-evident?
A: Yes -- SHA-256 hash chain; Tampered Audit attack demonstrated live on a copy.

Q: Can a viewer approve a plan?
A: No -- role-based JWT claims validated server-side; viewer gets 403 Forbidden.

Q: What is Safe Mode?
A: Mock LLM, cached road graph, offline map fallback. Demo completes under 4 minutes.

Q: How many tests?
A: 63+ pytest tests covering verification, allocation bounds, security, audit chain, WebSocket, USP invariants.

Q: Is any outcome hard-coded?
A: No -- all computed at runtime by real engines (CP-SAT, VerificationAgent, AuditChain).

Q: How does the map work offline?
A: MapLibre falls back to road-graph edges as SVG/Canvas lines on dark background using cached OSM graph nodes.

Q: What does the counterfactual show?
A: Best vs runner-up assignment: ETAs, costs, delta -- human-readable answer to why this unit.
