# CrisisMesh: 4-Minute Live Demo Presentation Script

**Domain 4: Crisis Command — Multi-Agent Coordination Control Room**

---

## Act 1: Initial Ingestion & Verification (0:00 – 1:00)
- **Action**: Click `[1] Start T0` in Presenter Controls.
- **Visuals**:
  - Ingestion of 3 emergency incidents across South-East Bengaluru (Silk Board, HSR Layout, Koramangala).
  - Verification Engine processes reports using Bayesian sequential updating and physical water-level sensor telemetry.
  - Incident 1 & 2 are marked `CONFIRMED` (green); Incident 3 (unverified citizen report) receives `UNVERIFIED` (amber).
- **Voiceover / Key Talking Point**:
  > *"CrisisMesh separates LLMs from decision-making. LLMs read and extract; deterministic Bayesian verification corroborates evidence against physical sensors. Notice that Incident 3 is unverified—our solver will treat it with mathematical skepticism."*

---

## Act 2: Uncertainty-Aware CP-SAT Allocation & Ed25519 Approval (1:00 – 2:00)
- **Action**: Click `Approve Plan` in the Top Bar.
- **Visuals**:
  - CP-SAT solver generates optimal allocation with 3 assignments.
  - Unit `amb_01` receives a `PROVISIONAL` assignment to `inc_t0_03`.
  - Commander checks the explicit confirmation box for `amb_01` and signs with Ed25519 digital signature.
  - Plan is dispatched and audit block is appended to the SHA-256 hash chain.
- **Voiceover / Key Talking Point**:
  > *"Rather than refusing to act or recklessly committing fleet, CrisisMesh issues a provisional dispatch bounded by minimax false-alarm costs. The human commander authorizes dispatch via an Ed25519 signature binding the plan hash and confirmation decisions."*

---

## Act 3: T+10 Dynamic Churn, Road Flooding & Veto Loop (2:00 – 3:00)
- **Action**: Click `[2] Step T+10`.
- **Visuals**:
  - Critical life-threatening submerged SUV reported in Outer Ring Road underpass.
  - `amb_02` suffers engine hydrostatic lock (`UNAVAILABLE`).
  - Approach roads to the underpass are physically inundated.
  - ImpactAgent inspects shortest paths and issues an unscripted `Veto` on the blocked route.
  - ResourceAgent performs a low-churn re-solve ($\lambda=60$), preserving en-route units and allocating idle `rescue_02`.
- **Voiceover / Key Talking Point**:
  > *"When disaster strikes dynamically, standard solvers reallocate units chaotically. CrisisMesh's low-churn objective penalizes switching ($\lambda=60$), preserving active rescue missions while rerouting around flooded corridors validated by the ImpactAgent's veto loop."*

---

## Act 4: Live OWASP Attack Defense & USP Proof (3:00 – 3:45)
- **Action**: Press `[A]` for Attacks Drawer, trigger `Prompt Injection` and `Forged Approval`. Press `[U]` for USP Proof.
- **Visuals**:
  - Prompt injection override attempt is instantly quarantined by IngestionGateway.
  - Forged signature attack blocked by cryptographic `ApprovalGate`.
  - USP Panel live graph confirms $\text{Robust Worst-Case Cost } (24.0) \le \text{Naive Worst-Case Cost } (58.0)$.
- **Voiceover / Key Talking Point**:
  > *"CrisisMesh is hardened against all OWASP Top 10 for LLMs. Every state change is immutably recorded in our tamper-evident hash chain."*

---

## Act 5: Summary & Close (3:45 – 4:00)
- **Action**: Show clean audit chain status badge in TopBar.
- **Summary**: 8 autonomous agents, mathematical optimization, cryptographic security, zero single points of failure.
