# CrisisMesh: Multi-Agent Architecture Specification (AGENTS.md)

## 1. System Overview & Core Philosophy
CrisisMesh is a multi-agent crisis coordination system designed for urban flood emergency response in city control rooms (e.g., Bengaluru hotspots: Silk Board, Bellandur, Koramangala, Marathahalli, HSR Layout).

### Non-Negotiable Invariants:
1. **LLMs READ and EXPLAIN. Algorithms DECIDE. Humans APPROVE.**
   - An LLM never allocates resources. Resource allocation is strictly executed by an OR-Tools CP-SAT solver.
2. **Untrusted Data Isolation**:
   - All incoming citizen report text is untrusted data, never instructions. The extractor LLM operates in quarantine with zero tools, zero secrets, and outputs strictly validated JSON matching a Pydantic schema. Raw report text never reaches the solver or command agent.
3. **Strong Typing & Runtime Enforcement**:
   - Every inter-agent message is a typed Pydantic v2 `Message` object. Disallowed tool invocations or unauthorized message dispatches trigger a `PermissionViolation`, publish an alert to the message bus, and appear in the live audit trace.
4. **Human-in-the-Loop Sovereign Control**:
   - Consequential field actions require explicit human commander approval cryptographically sealed with Ed25519 signatures and bound to plan hashes.
5. **Tamper-Evident Auditability**:
   - Every event, message, decision, and approval is appended to a SHA-256 hash-chained audit log.

---

## 2. The Seven Specialized Agents

| Agent | Core Role | Allowed Tools | Input Model | Output Model | LLM / Engine |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Supervisor** | Lifecycle coordinator & event router; runs selective re-plans. | `get_active_agents`, `dispatch_event`, `check_budget` | `CrisisEvent` / State | `SupervisorRouteDecision` | Deterministic State Controller |
| **Situation** | Ingests untrusted reports, sanitizes text, extracts structured facts. | *None (Zero tools, quarantined)* | `RawReportPayload` | `IncidentRecord` | LLM (Extraction prompt, JSON mode) |
| **Verification** | Validates reports, clusters duplicates, checks sensor agreement. | `credibility_scorer`, `duplicate_clusterer`, `labeler` | `IncidentRecord` | `VerificationResult` | Pure Deterministic Engine |
| **Impact** | Analyzes cascading hazards on road graphs & assesses accessibility. | `road_graph_engine`, `route_evaluator`, `hospital_reachability` | `List[IncidentRecord]` | `ImpactAssessment` | OSMnx / NetworkX Engine |
| **Resource** | Computes optimal multi-unit dispatch plans under constraints. | `cpsat_solver`, `diff_plans` | `ResourceRequest` | `PlanProposal` | OR-Tools CP-SAT Deterministic Solver |
| **Guardian** | Continuous security & policy sentry; inspects all outputs. | `policy_validator`, `audit_verifier`, `safety_gate` | `AgentMessage` / `PlanProposal` | `GuardianVerdict` | Deterministic Rules + Safety Monitor |
| **Command** | Synthesizes briefings, explains plan diffs & "why-not" runner-ups. | *None (Zero tools)* | `ApprovedStateSummary` | `CommanderBriefing` | LLM (Briefing prompt, JSON mode) |

---

## 3. Agent Communication & The Message Bus

Agents **never** call each other directly or share mutable objects. All communications flow through a typed `MessageBus`.

### Message Schema:
```python
class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    receiver: str
    type: str
    payload: Dict[str, Any]
    trace_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### Runtime Permission Manifest:
Each agent defines a strict `PermissionManifest`:
- `allowed_tools`: Set of tool names the agent is permitted to execute.
- `allowed_inbound`: Set of message types the agent can consume.
- `allowed_outbound`: Set of message types the agent can emit.

```python
class PermissionManifest(BaseModel):
    allowed_tools: Set[str] = Field(default_factory=set)
    allowed_inbound: Set[str] = Field(default_factory=set)
    allowed_outbound: Set[str] = Field(default_factory=set)
```

**Enforcement Rule**: If an agent attempts to invoke a tool outside its manifest:
1. A `PermissionViolation` exception is raised.
2. A `SecurityAlert` event is published to the `MessageBus`.
3. The event is written to the SHA-256 audit log and surfaced on the UI agent trace timeline.

---

## 4. Key Agent-to-Agent Interaction Protocols

### Protocol 1: Resource $\leftrightarrow$ Impact VETO Negotiation Loop (Max 3 Rounds)
1. **Resource** proposes a `PlanProposal` based on incident priority and unit proximity.
2. **Impact** runs reachability and travel-time calculations on the road graph (e.g. accounting for flooded underpasses).
3. If an allocated unit cannot reach an incident within critical time or a route is submerged:
   - Impact emits `PlanVeto(plan_id, infeasible_assignments=[(unit_id, incident_id)], reason)`.
4. **Resource** ingests the Veto as hard negative constraints and re-solves via CP-SAT.
5. This loop repeats for a maximum of **3 rounds**. If still unresolvable, the system flags the conflict to the Commander.

### Protocol 2: Verification $\rightarrow$ Situation Clarification Loop
1. When **Verification** processes an `IncidentRecord` and detects conflicting coordinates, ambiguous landmarks, or contradictory severity:
   - Verification emits a `ClarificationRequest(incident_id, missing_fields, contradiction_details)` directed to **Situation**.
2. **Situation** re-examines the source payload with a focused extraction pass and emits `ClarificationResponse`.

### Protocol 3: Guardian Oversight & Interception
1. **Guardian** intercepts every agent output and proposed action before it reaches human review or execution.
2. Evaluates safety invariants:
   - No double-booking of units.
   - No excessive resource commitment to low-credibility incidents.
   - Zero dispatch without a valid Ed25519 signature.
3. Verdicts:
   - `ALLOW`: Proposal proceeds to Command / Human.
   - `BLOCK`: Proposal rejected; sent back with violation report.
   - `ESCALATE_TO_HUMAN`: Flags urgent anomalous condition requiring immediate human commander intervention.

---

## 5. LangGraph Orchestration & Human Approval Interrupt

Orchestration is implemented using **LangGraph** (`StateGraph`):
- **Shared State**:
  - `incidents`: Dict[str, IncidentRecord]
  - `verification_labels`: Dict[str, VerificationResult]
  - `impact_report`: Optional[ImpactAssessment]
  - `current_plan`: Optional[PlanProposal]
  - `previous_approved_plan`: Optional[PlanProposal]
  - `pending_approvals`: List[ApprovalRequest]
  - `message_log`: List[Message]
  - `audit_chain`: List[Dict[str, Any]]
- **Conditional Edges**: Dynamic routing based on Supervisor decisions and negotiation counters.
- **Checkpointer**: Preserves full state history across transitions.
- **Human Approval Interrupt**: Execution halts at an explicit interrupt node prior to dispatch. The commander reviews the plan, plan diff, and runner-up explanations, providing an Ed25519-signed authorization to resume execution.
