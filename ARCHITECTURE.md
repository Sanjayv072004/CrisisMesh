# CrisisMesh: System Architecture & Design Specification

## 1. Executive Summary & Problem Context
CrisisMesh is an AI-assisted urban crisis coordination system developed for **GATEWAYS 2026 (Domain 4: Crisis Command)**. Operating in emergency control rooms during acute urban flood disasters (demonstrated on Bengaluru hotspots including Silk Board, Bellandur, Koramangala, an Outer Ring Road underpass, Marathahalli, and HSR Layout), CrisisMesh assists human incident commanders by filtering noise, analyzing cascading infrastructure impacts, and calculating provably optimal resource allocations.

---

## 2. Core Design Principles
1. **LLMs READ and EXPLAIN. Algorithms DECIDE. Humans APPROVE.**
   - LLMs are never entrusted with resource allocation. An OR-Tools CP-SAT solver deterministically handles all multi-unit dispatch computations.
2. **Untrusted Data Isolation**:
   - Ingested citizen reports are treated as untrusted data. Extractor models operate with zero tools and strict schema validation.
3. **Provable Auditability**:
   - All state transitions, inter-agent messages, and approvals are sealed in a SHA-256 hash-chained audit log with `verify_chain()` validation.
4. **Cryptographic Commander Authority**:
   - No unit is dispatched without an Ed25519 digital signature binding the commander's identity, the plan hash, a nonce, and an expiration timestamp.
5. **Deterministic Offline Capability**:
   - The LLM adapter provides `mock`, `replay`, and `live` modes. The entire system is fully verifiable offline with canned deterministic schemas and cached road graphs.

---

## 3. The Three USP Pillars

### Pillar 1: Uncertainty-Aware Allocation
- **Problem**: In disasters, early high-severity reports are often unverified. Naive systems either discard them (causing fatal delays) or over-commit scarce ambulances to false alarms.
- **Solution**: The CP-SAT solver evaluates unverified incidents across dual probabilistic scenarios:
  $$\mathbb{E}[\text{Cost}] = p \cdot \text{Cost}(\text{True}) + (1 - p) \cdot \text{Cost}(\text{False})$$
  where $p = \text{credibility\_score}$.
- **Operational Reality**: Unverified incidents receive **provisional** assignments requiring field validation before deployment.
- **Demo Proof**: Real-time side-by-side solver cost breakdown comparing our expected-cost formulation against naive baseline algorithms.

### Pillar 2: Low-Churn Re-Planning
- **Problem**: When a mid-scenario change occurs (e.g., an underpass floods or a new report arrives), unconstrained re-optimization reshuffles the entire fleet, creating operational chaos.
- **Solution**: The solver objective explicitly penalizes churn:
  $$\text{Objective} = \text{Harm}(\text{Delays}) + \text{Cost}(\text{Wasted Dispatch}) + \lambda \sum \text{Redirected En-Route Units}$$
- **Operational Reality**: The system produces a granular `PlanDiff` with per-change rationale, cost-of-change metrics, and flags identifying actions requiring human review.
- **Demo Proof**: Plan Diff interface highlighting why units were maintained or rerouted, with runner-up explanations.

### Pillar 3: Security as Architecture
- **Problem**: AI systems parsing public messages are vulnerable to prompt injection, denial-of-service floods, and unauthorized command tampering.
- **Solution**: Multi-layered defense-in-depth:
  - Ingestion gateway: HMAC source authentication, token-bucket rate limiting, Unicode sanitization, spotlighting delimiters.
  - Quarantined LLM: Zero tools, strict Pydantic output validation.
  - Runtime permissions: Agents calling tools outside their manifest trigger immediate exceptions and security trace alerts.
  - Cryptographic approvals: Ed25519 signatures protect against forgery and replay.
  - Hash-chained audit logs: Prevent retroactive tampering.
- **Demo Proof**: Interactive Attack Panel firing OWASP Top 10 for LLM attacks, showing cards marked `BLOCKED by <layer> because <reason>`.

---

## 4. System Layer Architecture

```
+---------------------------------------------------------------------------------+
|                       INGESTION GATEWAY & SECURITY LAYER                        |
|  - HMAC Authentication  - Token-Bucket Rate Limiter  - Spotlighting Sanitizer   |
|  - Prompt Injection Scanner  - Ed25519 Signature Verifier - SHA-256 Audit Log   |
+---------------------------------------------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                    MULTI-AGENT ORCHESTRATION (LangGraph)                        |
|                     StateGraph  -  Shared Typed State                           |
|                                                                                 |
|   [Supervisor] ----> [Situation] <----+                                         |
|        |                   |          | (Clarification Loop)                    |
|        v                   v          |                                         |
|    (Selective       [Verification] ---+                                         |
|     Re-plan)               |                                                    |
|                            v                                                    |
|                        [Impact] <==========+                                    |
|                            |               | (VETO Negotiation Loop,            |
|                            v               |  max 3 rounds)                     |
|                       [Resource] ==========+                                    |
|                            |                                                    |
|                            v                                                    |
|                       [Guardian] (Safety Check: ALLOW / BLOCK / ESCALATE)       |
|                            |                                                    |
|                            v                                                    |
|                        [Command] (Briefings & Counterfactuals)                  |
|                            |                                                    |
|                            v                                                    |
|                 [HUMAN COMMANDER APPROVAL] (LangGraph Interrupt)                |
|                            | (Signed Ed25519)                                   |
|                            v                                                    |
|                       [DISPATCH]                                                |
+---------------------------------------------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                         CORE DETERMINISTIC ENGINES                              |
|  - Impact Engine: OSMnx / NetworkX Bengaluru Road Graph                         |
|  - Verification Engine: Bayesian Credibility & TF-IDF Duplicate Clustering      |
|  - Allocation Engine: Google OR-Tools CP-SAT Solver                             |
+---------------------------------------------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                         FASTAPI & WEBSOCKET TRACE                               |
|  - REST Endpoints  - WebSocket Live Stream  - OpenAPI Schema Export             |
+---------------------------------------------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
|                       COMMANDER DASHBOARD (Next.js UI)                          |
|  - MapLibre Live Map  - Plan Diff Panel  - Agent Trace Stream  - Attack Panel   |
+---------------------------------------------------------------------------------+
```
