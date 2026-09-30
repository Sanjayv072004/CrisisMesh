# CrisisMesh

> **Multi-Agent Emergency Response & Resource Coordination System**  
> *GATEWAYS 2026 - Domain 4: Crisis Command*

---

## Overview
CrisisMesh is an AI-assisted emergency coordination platform engineered for city control rooms managing complex urban flood crises. Operating on real OpenStreetMap road graphs (demonstrated on Bengaluru hotspots: Silk Board, Bellandur, Koramangala, Marathahalli, Outer Ring Road underpass, and HSR Layout), CrisisMesh pairs specialized AI agents with a **deterministic operations research solver** and a **cryptographic human approval gate**.

---

## Core Invariants
- **LLMs READ and EXPLAIN. Algorithms DECIDE. Humans APPROVE.**
- Resource dispatch is **never** left to an LLM; it is strictly computed by an OR-Tools CP-SAT solver.
- All untrusted civilian report text is quarantined, sanitized, and spotlighted; extractor LLMs possess zero tools and zero system secrets.
- Inter-agent coordination is strictly governed by typed messages across a message bus with runtime permission enforcement.
- Cryptographic approvals: No vehicle dispatches without an **Ed25519 digital signature** binding the commander's identity and the plan hash.
- Tamper-evident **SHA-256 hash-chained audit logging** records all decisions and approvals.

---

## The Three USP Pillars
1. **Uncertainty-Aware Allocation**: Optimizes across dual scenarios (report true vs. false) weighted by credibility, ensuring optimal decisions under incomplete knowledge while provisioning unverified incidents.
2. **Low-Churn Re-Planning**: Evaluates cascading road blockages with switching penalties ($\lambda \times \text{redirected en-route units}$) to prevent operational chaos.
3. **Security as Architecture**: Multi-tier defense including prompt injection screening, HMAC authentication, runtime permission manifests, and an interactive OWASP Top 10 Attack Panel.

---

## Multi-Agent Architecture
CrisisMesh features seven specialized agents orchestrated via **LangGraph**:
1. **Supervisor**: Event router, selective re-planner, and negotiation step manager.
2. **Situation**: Quarantined fact extractor converting free text into typed `IncidentRecord` models.
3. **Verification**: Bayesian credibility scoring, sensor corroboration, and spatiotemporal duplicate clustering.
4. **Impact**: Road-network reachability, cut-off zones, and hospital delay modeling (OSMnx / NetworkX).
5. **Resource**: CP-SAT optimization engine formulating dispatch plans under constraints.
6. **Guardian**: Independent safety sentry reviewing every output with `ALLOW`, `BLOCK`, or `ESCALATE` verdicts.
7. **Command**: Synthesizer producing commander briefings, plan diff rationales, and "why-not" counterfactuals.

---

## Directory Structure
```
CrisisMesh/
├── AGENTS.md                  # Detailed multi-agent specification & contracts
├── ARCHITECTURE.md            # System architecture, data flow & security design
├── README.md                  # Project overview & quickstart
├── backend/
│   ├── app/
│   │   ├── gateway/           # Ingestion, sanitization, rate-limiting & HMAC
│   │   ├── agents/            # Base agent, manifests, and the 7 specialized agents
│   │   ├── engines/           # Road graph, CP-SAT solver, verification engine
│   │   ├── security/          # Ed25519 signing, hash-chained audit, policy rules
│   │   ├── api/               # FastAPI routes & WebSocket event streaming
│   │   ├── models/            # Pydantic v2 domain schemas & messages
│   │   ├── audit/             # Audit store & chain verification
│   │   └── orchestration/     # LangGraph StateGraph, checkpointer, human interrupt
│   ├── tests/                 # Unit, integration, security & attack test suites
│   └── requirements.txt       # Python dependencies
├── data/                      # Cached Bengaluru road graphs & scenario fixtures
├── frontend/                  # Next.js, MapLibre, Tailwind & Zustand dashboard
└── docs/                      # Technical documentation & STRIDE threat model
```

---

## Phase Roadmap
- [x] **Phase 0**: Repo, rules, contracts & architecture specification.
- [ ] **Phase 1**: Foundations (road graph, CP-SAT solver, deterministic verification engine).
- [ ] **Phase 2**: Agent framework (typed message bus, permissions, LLM adapter with mock mode).
- [ ] **Phase 3**: The 7 agents & LangGraph orchestration (veto negotiation, selective re-plan).
- [ ] **Phase 4**: Security layer (gateway, injection scan, Ed25519 signing, audit chain).
- [ ] **Phase 5**: API, WebSocket streaming & human approval gate.
- [ ] **Phase 6**: Commander Dashboard (live map, plan diff, agent trace).
- [ ] **Phase 7**: Demo controls, interactive Attack Panel & USP proof panel.
- [ ] **Phase 8**: Hardening, Docker Compose & Round 1 doc-vs-reality audit.
