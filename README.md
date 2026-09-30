# CrisisMesh

> **Multi-agent AI coordination for real-time disaster response** — built for the ADK Hackathon 2025.

[![Tests: 66 passed](https://img.shields.io/badge/tests-66%20passed-brightgreen)](backend/tests)
[![ruff: passing](https://img.shields.io/badge/ruff-passing-brightgreen)](pyproject.toml)
[![ESLint: 0 errors](https://img.shields.io/badge/eslint-0%20errors-brightgreen)](.eslintrc.json)

---

## What is CrisisMesh?

CrisisMesh deploys a **7-agent LangGraph pipeline** that ingests disaster reports, cross-validates them against IoT sensors, solves a CP-SAT resource allocation problem, guards against adversarial prompt injection, and streams live decisions to an interactive operations dashboard — all within seconds.

### Architecture in 60 seconds

```
Sensor Data ──► VerificationEngine ──► SituationAgent
                                           │
                              ┌────────────▼────────────┐
                              │  LangGraph Orchestrator  │
                              │  ┌─────────────────────┐ │
                              │  │  SupervisorAgent    │ │
                              │  │  ResourceGuardian   │ │
                              │  │  CommandAgent       │ │
                              │  │  CommunicationsAgt  │ │
                              │  │  ImpactAgent        │ │
                              │  └─────────────────────┘ │
                              └────────────┬────────────┘
                                           │
                              CP-SAT Solver (Google OR-Tools)
                                           │
                              WebSocket Stream ──► React Dashboard
```

### Key USPs (all provably tested)

| Claim | Test |
|---|---|
| Low-churn replanning (units reassigned only when needed) | `test_low_churn_replanning_and_diff` |
| Adversarial prompt-injection blocked by Guardian | `test_fake_report_attack_blocked` |
| Uncertainty-aware provisional assignments | `test_cpsat_solver_and_uncertainty_aware_provisional_assignment` |
| 3-veto cycle limit prevents infinite loops | `test_veto_loop_stops_at_three_rounds` |
| Graceful LLM degradation (fallback to mock) | `test_chaos_llm_crash_triggers_graceful_degradation` |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- Git

### 1 — Clone and install

```bash
git clone https://github.com/<your-org>/crisismesh
cd crisismesh

# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2 — Run in demo mode (no API keys needed)

Open **two** terminals:

**Terminal 1 — Backend:**
```bash
CRISISMESH_DEMO_MODE=true python -m uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
NEXT_PUBLIC_DEMO_AUTOLOGIN=true npm run dev
```

Then open **http://localhost:3000**

### 3 — Demo keyboard shortcuts

| Key | Action |
|---|---|
| `P` | Toggle presenter controls |
| `1` | Start scenario at T=0 (Silk Board flood) |
| `2` | Advance to T+10 min (roads blocked, replanning) |
| `A` | Open attack panel (prompt injection demo) |
| `U` | Open USP proof panel (3 tabs of evidence) |
| `R` | Reset scenario |
| `Esc` | Close any open panel |

### 4 — Demo flow (5 minutes)

1. **T0** — 3 incidents arrive. Agents verify against sensors, solve CP-SAT, stream a plan.
2. **T+10** — Road blocked. Impact agent recalculates, veto triggers replanning (only moved units shown in red).
3. **Attack panel** — Send a fake report. Guardian's VerificationEngine tags it `PROVISIONAL_ISOLATED`. The dashboard shows "BLOCKED by VerificationEngine".
4. **USP panel** — See:
   - *Low-churn diff*: only 1 of 3 units moved
   - *Uncertainty bands*: confidence scores per assignment
   - *Blockchain audit hash*: plan signed and stored

---

## Docker (Recommended for judging)

### Run everything with one command

```bash
# Build and start (no internet needed after build)
docker compose up -d

# Optional: with Postgres + Redis
docker compose --profile postgres --profile redis up -d
```

Verify it's up:
```bash
curl http://localhost:8000/health   # {"status":"ok"}
curl http://localhost:3000          # Dashboard HTML
```

### What's in the compose?

| Service | Port | Network |
|---|---|---|
| `backend` | 8000 | `public-net` (external) + `internal-net` (isolated) |
| `frontend` | 3000 | `public-net` only |
| `postgres` | (internal only) | `internal-net` |
| `redis` | (internal only) | `internal-net` |

Security: solver and audit store are on `internal-net` (no external internet).
All containers run as non-root (UID 10001) with `no-new-privileges`.

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full technical reference.

### Agent Pipeline

```
SituationAgent   — Parses and structures incoming crisis reports
SupervisorAgent  — Coordinates the agent graph, manages veto cycles
ResourceGuardian — Validates plans, blocks double-bookings & injections
CommandAgent     — Converts plans to executable unit assignments
ImpactAgent      — Road network analysis, unreachable node detection
CommAgent        — Generates public advisories and unit notifications
SituationAgent   — Final situation summary for human commander
```

### Security Model

- **Prompt injection**: Every LLM output passes through `InjectionDetector` + schema validation. Malformed or adversarial content raises `ValidationError`, not hallucination.
- **JWT auth**: Tokens kept in memory (not localStorage). Short-lived tokens for WebSocket.
- **HMAC sensor auth**: IoT sensors sign each payload. Replays rejected.
- **Rate limiting**: Per-IP, per-user, per-route sliding window.

Full threat model: [`docs/threat-model.md`](docs/threat-model.md) (STRIDE table, 16 entries).

---

## Running Tests

```bash
# All 66 backend tests
python -m pytest backend/tests/ -v

# Single category
python -m pytest backend/tests/test_phase3_orchestration.py -v
python -m pytest backend/tests/test_chaos.py -v

# Full quality gate
python scripts/verify.py
```

### Test categories

| File | Tests | What it covers |
|---|---|---|
| `test_phase3_orchestration.py` | 11 | 7-agent pipeline, veto cycles, checkpointing |
| `test_api_phase5.py` | 14 | REST API, WebSocket, HMAC, rate limiting |
| `test_engines.py` | 4 | CP-SAT solver, routing, low-churn diff |
| `test_verification.py` | 7 | Sensor fusion, credibility, decay |
| `test_impact.py` | 3 | Road blocking, unreachable detection |
| `test_chaos.py` | 3 | LLM crash, timeout, full pipeline death |
| `test_gateway.py` | 18 | Injection detection, rate limiting, auth |
| `test_agents_phase4.py` | 6 | Individual agent unit tests |

---

## Quality Gates

Run `python scripts/verify.py` (or `make verify`) to execute all gates:

| Gate | Command | Status |
|---|---|---|
| Secret scan | `python scripts/scan_secrets.py` | 0 secrets in 11 commits |
| Backend lint | `python -m ruff check backend/` | 0 errors |
| Backend types | `python -m mypy backend/app --ignore-missing-imports` | 24 annotation notes (non-blocking) |
| Backend tests | `python -m pytest backend/tests/ -v` | **66 passed** |
| Frontend lint | `npm run lint` (eslint) | 0 errors, 0 warnings |
| Frontend types | `npx tsc --noEmit` | 0 errors |
| Frontend build | `npm run build` | compiled successfully |
| npm audit | `npm audit` | 3 known CVEs (documented) |

### Known npm vulnerabilities (documented, not silently ignored)

| Package | Severity | CVE | Why not fixed |
|---|---|---|---|
| `maplibre-gl <=6.4.0` | Critical | GHSA-jrc7-96c5-q579 | Fix requires breaking upgrade to 6.11.2 |
| `next ^14.2.15` | Critical | Multiple | Fix requires upgrade to v16 (breaking) |
| `postcss <=8.5.22` | High | Path traversal | Tied to next version |

**Mitigation**: Frontend runs offline in Safe Mode during demo. CSP headers (`connect-src 'self'`) prevent cross-origin data exfiltration even if XSS triggered.

---

## Project Structure

```
CrisisMesh/
├── backend/
│   ├── app/
│   │   ├── agents/          # 7 LangGraph agents
│   │   ├── api/             # FastAPI routes, auth, WebSocket
│   │   ├── core/            # Logging, config
│   │   ├── engines/         # CP-SAT solver, road graph
│   │   ├── gateway/         # Rate limiter, injection detector
│   │   ├── models/          # Pydantic schemas
│   │   └── orchestration/   # LangGraph graph definition
│   ├── tests/               # 66 pytest tests
│   └── requirements.txt     # Pinned dependencies
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js 14 App Router pages
│   │   ├── components/      # React components
│   │   └── store/           # Zustand state management
│   └── package.json
├── docs/
│   ├── architecture.md      # Full technical reference
│   ├── threat-model.md      # STRIDE table
│   └── security-testing-summary.md
├── scripts/
│   ├── scan_secrets.py      # Git history scanner
│   └── verify.py            # Full quality gate
├── docker-compose.yml       # Production deployment
├── Makefile                 # Development shortcuts
└── pyproject.toml           # ruff + pytest config
```

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built in 8 phases over the ADK Hackathon sprint. Phase 8: hardened, packaged, and ready for judging.*
