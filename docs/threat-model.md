# CrisisMesh STRIDE Threat Model & Security Assurance Matrix

This document provides a comprehensive threat model of the CrisisMesh architecture based on the Microsoft **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) mapped directly to our defense-in-depth mitigations and automated verification tests.

---

## 1. System Security Boundary & Assumptions

CrisisMesh operates in high-stress emergency control rooms ingesting data from untrusted public channels (citizen mobile reports, SMS) and semi-trusted infrastructure sensors (IoT water gauges, traffic feeds). 

### Trust Boundaries:
1. **Public Perimeter**: Untrusted network ingesting citizen reports and HTTP API requests.
2. **Gateway Defense Perimeter**: Rate limiting, HMAC authentication, spotlighting sanitization, and regex heuristic injection detectors.
3. **Multi-Agent Orchestration Perimeter**: Isolated LangGraph state machine. Zero LLM tools permitted for situation understanding. LLMs explain and format; OR-Tools CP-SAT algorithm decides.
4. **Command & Dispatch Authority**: Ed25519 digital signature boundary. Automated agents are cryptographically prevented from issuing dispatch orders without explicit human commander key signature.
5. **Audit Chain**: Append-only SHA-256 cryptographic hash chain verifying tamper-evident history.

---

## 2. Comprehensive STRIDE Matrix

| # | STRIDE Category | Threat Description | Affected Component | Architectural Mitigation | Verifying Test |
|---|---|---|---|---|---|
| **T01** | **Spoofing** | Attacker impersonates legitimate citizen or emergency responder with fabricated incident reports | Ingestion Gateway & Verification Agent | HMAC token authentication gate for authenticated sources; Bayesian multi-source credibility scoring ($k$ independent corroborations required) | `backend/tests/test_verification.py::test_thirty_duplicate_reports_stay_unverified` |
| **T02** | **Spoofing** | Compromised IoT sensor transmits fabricated low/high water levels to redirect rescue units | Ingestion Gateway & Sensor Registry | SHA-256 HMAC signature required on every sensor payload (`X-Sensor-Signature`) with per-sensor secret keys; replay prevention via timestamp window | `backend/tests/attacks/test_owasp_attacks.py::test_spoofed_sensor_data_invalid_hmac` |
| **T03** | **Spoofing** | Rogue actor attempts to approve dispatch plan by forging human incident commander signature | Approval Gate (`routes_plan.py`) | Ed25519 asymmetric cryptography: plan approved only if signature verifies against commander's registered public key | `backend/tests/attacks/test_owasp_attacks.py::test_llm06_forged_commander_approval_wrong_key` |
| **T04** | **Tampering** | Malicious insider or attacker alters approved dispatch plan mid-transit before dispatch execution | Approval Gate & State Manager | Plan payload is hashed (`SHA-256`); signature verification binds both commander ID and exact `plan_hash`. Content mismatch causes immediate rejection | `backend/tests/attacks/test_owasp_attacks.py::test_llm06_altered_plan_after_approval_hash_mismatch` |
| **T05** | **Tampering** | Attacker attempts to modify, inject, or delete historic audit trail records to conceal sabotage | Cryptographic Audit Log (`audit/chain.py`) | Every audit entry embeds the SHA-256 hash of the previous record. `verify_chain()` detects any single bit modification, missing node, or re-ordering | `backend/tests/attacks/test_owasp_attacks.py::test_llm08_audit_tampering_detected` |
| **T06** | **Tampering** | Adversary injects adversarial prompt text into citizen report to hijack agent reasoning (OWASP LLM01) | Gateway Sanitizer & Ingestion Pipeline | Spotlighting delimiters (`<<<RAW_UNTRUSTED_CONTENT>>>`), zero-width Unicode stripping, heuristic injection patterns regex scanner, low extraction confidence quarantine | `backend/tests/attacks/test_owasp_attacks.py::test_llm01_prompt_injection_quarantined_and_low_confidence` |
| **T07** | **Repudiation** | Incident commander denies authorizing an emergency unit reassignment or controversial dispatch | Command Agent & Audit Store | Irrefutable Ed25519 digital signature bound to plan hash, UTC timestamp, and unique nonce recorded permanently in immutable audit log | `backend/tests/test_api_phase5.py::test_full_flow_through_api` |
| **T08** | **Repudiation** | Automated agent disputes rationale for vetoing resource route | Supervisor & Impact Agent | Inter-agent trace messages are cryptographically sealed in the audit store with deterministic agent ID and timestamp | `backend/tests/test_phase3_orchestration.py::test_t0_run_produces_plan_and_involves_all_seven_agents` |
| **T09** | **Information Disclosure** | Raw citizen PII or unverified allegations leaked to unauthorized LLM context or operator displays | Situation & Command Agents | Raw citizen text is strictly quarantined in Situation Agent. Command Agent receives only structured incident summaries and coordinate nodes | `backend/tests/test_phase3_orchestration.py::test_command_never_receives_raw_report_text` |
| **T10** | **Information Disclosure** | JWT stolen from browser storage by Cross-Site Scripting (XSS) attack | Frontend Auth Client | JWT is held strictly in memory in `ApiClient` private variable; never written to `localStorage` or `sessionStorage`. Browser CSP headers block inline script injection | `frontend/next.config.mjs` & manual audit |
| **T11** | **Denial of Service** | Botnet floods emergency gateway with 30+ duplicate reports to exhaust server resources (OWASP LLM04) | Ingestion Gateway | Dual-layer TokenBucket rate limiter (per IP and per source ID); TF-IDF deduplication merges semantic duplicates without triggering replans | `backend/tests/attacks/test_owasp_attacks.py::test_llm04_dos_flood_duplicate_reports_burst` |
| **T12** | **Denial of Service** | High volume of HTTP requests exhausts API worker threads | FastAPI Middleware | `RequestSizeLimitMiddleware` (max 1MB payload), strict timeouts on external calls, connection limits | `backend/tests/test_api_phase5.py::test_request_size_limit` |
| **T13** | **Denial of Service** | Complex incident network causes CP-SAT solver combinatorial explosion | Allocation Engine | OR-Tools CP-SAT solver configured with explicit deterministic timeout (max 5.0 seconds); falls back to greedy heuristic if deadline exceeded | `backend/tests/test_engines.py::test_cpsat_solver_and_uncertainty_aware_provisional_assignment` |
| **T14** | **Elevation of Privilege** | Read-only spectator/viewer role attempts to approve emergency dispatch plan (OWASP LLM06) | RBAC Permission Gate (`api/auth.py`) | Role hierarchy enforced on every endpoint. Viewer role lacks `DISPATCH_APPROVE` permission; request rejected with HTTP 403 Forbidden | `backend/tests/attacks/test_owasp_attacks.py::test_llm06_privilege_escalation_viewer_cannot_approve_plan` |
| **T15** | **Elevation of Privilege** | Compromised LLM attempts to call unit dispatch tool directly (OWASP LLM06 Excessive Agency) | Agent Framework (`agents/base/agent.py`) | Strict `PermissionManifest` runtime gate: agents attempting to invoke unauthorized tools immediately trigger `SecurityException` and trace alerts | `backend/tests/attacks/test_owasp_attacks.py::test_llm06_excessive_agency_agent_cannot_call_dispatch_tool` |
| **T16** | **Elevation of Privilege** | Attacker replays intercepted valid commander signature for a previous plan on a new emergency | Approval Gate Nonce Store | Nonce replay cache: each nonce is valid for a single use within a 300s expiration window; replay rejected | `backend/tests/attacks/test_owasp_attacks.py::test_llm06_replayed_commander_approval_rejected` |

---

## 3. Defense-in-Depth Summary

CrisisMesh enforces security across 5 distinct architectural rings:
1. **Perimeter Network**: Isolated Docker networks (`internal-net` vs `public-net`), non-root container users, read-only root filesystems.
2. **Application Gateway**: Token-bucket rate limiting, HMAC validation, Unicode normalization, zero-width stripping.
3. **Agent Runtime**: Permission manifests, zero-tool extraction LLMs, schema-enforced Pydantic parsing.
4. **Algorithmic Authority**: Allocation decisions computed exclusively by Google OR-Tools CP-SAT solver, never by probabilistic generative models.
5. **Cryptographic Sealing**: Ed25519 digital signatures on all dispatch commands + SHA-256 chained audit ledger.
