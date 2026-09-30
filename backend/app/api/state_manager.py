"""CrisisMesh State Manager: Orchestrator Coordination, Scenario Lifecycle & Event Streaming."""
from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
import time
from typing import Dict, List, Optional, Any, Tuple
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.orchestration.state import DisasterState, StateSnapshot
from backend.app.gateway.pipeline import IngestionGateway
from backend.app.gateway.auth import HMACAuthenticator
from backend.app.gateway.rate_limiter import TokenBucketRateLimiter
from backend.app.gateway.injection_detector import HeuristicInjectionDetector
from backend.app.security.crypto import ApprovalGate, CommanderKeyManager, SignedApproval
from backend.app.security.rbac import CommanderToken, Role
from backend.app.models.schemas import (
    IncidentRecord, Unit, Hospital, Plan, PlanDiff, SensorReading, SecurityEvent, UnitStatus
)
from backend.app.api.websocket import ws_manager

DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "scenario.json"


class CrisisStateManager:
    """Manages active disaster state, LangGraph checkpointing, and real-time WebSocket dispatches."""

    def __init__(self):
        self.bus = MessageBus()
        self.key_manager = CommanderKeyManager()
        self.approval_gate = ApprovalGate()
        self.orchestrator = CrisisMeshOrchestrator(bus=self.bus, approval_gate=self.approval_gate)

        # Ingestion Gateway
        auth = HMACAuthenticator()
        auth.register_source("sensor_silkboard_01", "shared-sensor-secret-key-32bytes!")
        auth.register_source("gauge_silkboard_01", "secret_key_gauge_silkboard")
        auth.register_source("gauge_bellandur_lake_02", "secret_key_bellandur_telemetry")
        auth.register_source("rain_hsr_01", "secret_key_rain_sensor_hsr")
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate_per_sec=2.0)
        detector = HeuristicInjectionDetector()
        self.gateway = IngestionGateway(authenticator=auth, rate_limiter=limiter, detector=detector)

        # Wire MessageBus to stream events over WebSocket
        self.bus.subscribe(self._on_bus_message)

        self.scenario_data: Dict[str, Any] = {}
        self.state: DisasterState = {}
        self.thread_id: str = ""
        self.config: Dict[str, Any] = {}
        self.is_playing: bool = False
        self.security_events: List[SecurityEvent] = []

        self.reset_scenario()

    def _on_bus_message(self, message: Any) -> None:
        """Callback receiving all inter-agent messages and forwarding to WebSockets."""
        ws_manager.emit(
            event_type="agent_message",
            payload=message.model_dump(mode="json") if hasattr(message, "model_dump") else dict(message),
            trace_id=getattr(message, "trace_id", "trace-bus"),
        )
        if getattr(message, "type", "") == "SecurityAlert":
            evt_payload = getattr(message, "payload", {}).get("event", {})
            ws_manager.emit(event_type="security_event", payload=evt_payload)

    def reset_scenario(self) -> StateSnapshot:
        """Reset operational state to clean startup based on data/scenario.json."""
        with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
            self.scenario_data = json.load(f)

        self.thread_id = f"crisis-run-{int(time.time()*1000)}"
        self.config = {"configurable": {"thread_id": self.thread_id}}

        self.state = {
            "incidents": {},
            "units": copy.deepcopy(self.scenario_data.get("units", [])),
            "hospitals": copy.deepcopy(self.scenario_data.get("hospitals", [])),
            "verification_labels": {},
            "impact_report": None,
            "current_plan": None,
            "previous_approved_plan": None,
            "plan_diff": None,
            "commander_briefing": None,
            "pending_approvals": [],
            "message_log": [],
            "negotiation_history": [],
            "active_agents": [],
            "scheduled_agents": [],
            "trigger_event_type": "initial_boot",
            "veto_count": 0,
            "step_budget": 20,
            "status": "INITIALIZED",
            "error": None,
            "_clarification_loop_count": 0,
        }

        self.security_events.clear()
        ws_manager.emit(
            event_type="scenario_status",
            payload={"action": "reset", "status": "INITIALIZED", "thread_id": self.thread_id},
        )
        return self.get_snapshot()

    def start_scenario(self) -> StateSnapshot:
        """Ingest T0 incidents and trigger initial LangGraph allocation run."""
        t0_incidents = {i["id"]: i for i in self.scenario_data.get("t0_incidents", [])}
        self.state["incidents"] = t0_incidents
        self.state["trigger_event_type"] = "new_report"
        self.state["status"] = "RUNNING_T0"

        # Invoke LangGraph: execution proceeds up to interrupt_before=["human_approval"]
        self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

        # Notify WebSocket subscribers of results
        ws_manager.emit(event_type="incident_updated", payload={"incidents": self.state.get("incidents", {})})
        if self.state.get("impact_report"):
            ws_manager.emit(event_type="impact_updated", payload=self.state["impact_report"])
        if self.state.get("current_plan"):
            ws_manager.emit(event_type="plan_proposed", payload=self.state["current_plan"])
            ws_manager.emit(
                event_type="approval_required",
                payload={
                    "plan_id": self.state["current_plan"]["plan_id"],
                    "plan_hash": self.approval_gate.compute_plan_hash(self.state["current_plan"]),
                    "briefing": self.state.get("commander_briefing", {}),
                }
            )

        ws_manager.emit(
            event_type="scenario_status",
            payload={"action": "start", "status": self.state.get("status")},
        )
        return self.get_snapshot()

    def step_scenario(self) -> StateSnapshot:
        """Inject T+10 change events (submerged car in underpass, Ambulance 2 failure) and re-plan."""
        t10_events = self.scenario_data.get("t10_change_events", [])
        if t10_events:
            t10_incident = t10_events[0]["incident"]
            self.state["incidents"][t10_incident["id"]] = t10_incident

        curr_plan = self.state.get("current_plan")
        if curr_plan:
            assigned_uids = [a["unit_id"] for a in curr_plan.get("assignments", [])]
            for u in self.state["units"]:
                if u["id"] == "amb_02":
                    u["status"] = "unavailable"
                elif u["id"] in assigned_uids:
                    u["status"] = "en_route"
                    u["current_target_id"] = next(
                        a["incident_id"] for a in curr_plan.get("assignments", []) if a["unit_id"] == u["id"]
                    )

        # Trigger selective re-plan
        self.state["trigger_event_type"] = "unit_status_change"
        self.state["active_agents"] = []

        # Fresh thread for selective re-plan
        self.thread_id = f"crisis-run-{int(time.time()*1000)}"
        self.config = {"configurable": {"thread_id": self.thread_id}}

        # Run re-plan up to next interrupt
        self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

        if self.state.get("plan_diff"):
            ws_manager.emit(event_type="plan_diff", payload=self.state["plan_diff"])
        if self.state.get("current_plan"):
            ws_manager.emit(event_type="plan_proposed", payload=self.state["current_plan"])
            ws_manager.emit(
                event_type="approval_required",
                payload={
                    "plan_id": self.state["current_plan"]["plan_id"],
                    "plan_hash": self.approval_gate.compute_plan_hash(self.state["current_plan"]),
                    "briefing": self.state.get("commander_briefing", {}),
                }
            )

        ws_manager.emit(
            event_type="scenario_status",
            payload={"action": "step", "status": self.state.get("status")},
        )
        return self.get_snapshot()

    async def play_scenario(self, speed: float = 1.0) -> None:
        """Progress scenario stages with speed-adjusted timing."""
        self.is_playing = True
        ws_manager.emit(event_type="scenario_status", payload={"action": "play", "speed": speed})

        # 1. Reset and Start
        self.reset_scenario()
        await asyncio.sleep(1.0 / speed)
        self.start_scenario()

        # 2. Auto-approve T0 if in play mode
        await asyncio.sleep(2.0 / speed)
        if self.state.get("current_plan"):
            self.approve_plan(
                plan_id=self.state["current_plan"]["plan_id"],
                auto_sign=True,
                commander_token=CommanderToken(
                    user_id="commander_auto",
                    public_key_hex=self.key_manager.get_public_key_hex(),
                )
            )

        # 3. Step to T+10
        await asyncio.sleep(3.0 / speed)
        self.step_scenario()
        self.is_playing = False

    def ingest_report(
        self, text: str, source_id: str, lat: float, lon: float, ip_address: str = "127.0.0.1"
    ) -> Dict[str, Any]:
        """Ingest report through security gateway and trigger reactive pipeline."""
        res = self.gateway.ingest_report(
            raw_text=text,
            source_id=source_id,
            lat=lat,
            lon=lon,
            ip_address=ip_address,
        )

        for event in res.security_events:
            self.security_events.append(event)
            self.bus.log_security_event(event.event_type, "IngestionGateway", event.model_dump())
            ws_manager.emit(event_type="security_event", payload=event.model_dump(mode="json"))

        if res.is_auth_rejected:
            return {"status": "AUTH_REJECTED", "is_quarantined": True, "security_events": [e.model_dump() for e in res.security_events]}
        if res.is_rate_limited:
            return {"status": "RATE_LIMITED", "is_quarantined": True, "security_events": [e.model_dump() for e in res.security_events]}

        if res.report:
            from datetime import datetime, timezone
            from backend.app.models.schemas import UnitType, VerificationLabel
            inc_id = f"inc_{res.report.id}"
            is_adversarial = res.report.metadata.get("is_adversarial", False)
            inc_obj = IncidentRecord(
                id=inc_id,
                title=f"Report from {source_id}",
                description=res.spotlit_text,
                lat=lat,
                lon=lon,
                severity=4 if not is_adversarial else 1,
                people_affected=2,
                required_unit_type=UnitType.AMBULANCE,
                is_life_threatening=False,
                reported_at=datetime.now(timezone.utc),
                confidence=res.report.metadata.get("confidence", 0.8),
                verification_label=VerificationLabel.UNVERIFIED if not is_adversarial else VerificationLabel.CONFLICTING,
                credibility_score=res.report.metadata.get("confidence", 0.5),
            )
            self.state["incidents"][inc_id] = inc_obj.model_dump(mode="json")
            self.state["trigger_event_type"] = "new_report"

            # Execute graph
            self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

            ws_manager.emit(event_type="incident_updated", payload={"incidents": self.state.get("incidents", {})})
            if self.state.get("current_plan"):
                ws_manager.emit(event_type="plan_proposed", payload=self.state["current_plan"])
                ws_manager.emit(
                    event_type="approval_required",
                    payload={
                        "plan_id": self.state["current_plan"]["plan_id"],
                        "plan_hash": self.approval_gate.compute_plan_hash(self.state["current_plan"]),
                        "briefing": self.state.get("commander_briefing", {}),
                    }
                )

            return {
                "report_id": res.report.id,
                "status": "INGESTED",
                "is_quarantined": res.is_quarantined,
                "confidence": inc_obj.confidence,
                "security_events": [e.model_dump() for e in res.security_events],
            }

        return {"status": "PROCESSED", "is_quarantined": res.is_quarantined, "security_events": []}

    def ingest_sensor(
        self, sensor_id: str, sensor_type: str, lat: float, lon: float, value: float, unit: str, signature_hex: str, flood_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Ingest authenticated sensor telemetry and update road graph reachability."""
        raw_text = f"sensor_id={sensor_id}&value={value}&type={sensor_type}"
        is_auth, auth_msg = self.gateway.auth.verify(sensor_id, raw_text.encode("utf-8"), signature_hex)

        if not is_auth:
            event = SecurityEvent(
                event_type="spoofed_source_hmac",
                severity="HIGH",
                agent_name="IngestionGateway",
                description=f"Rejected sensor telemetry from '{sensor_id}': {auth_msg}",
            )
            self.security_events.append(event)
            self.bus.log_security_event(event.event_type, "IngestionGateway", event.model_dump())
            ws_manager.emit(event_type="security_event", payload=event.model_dump(mode="json"))
            return {"status": "REJECTED", "reason": auth_msg}

        # If sensor confirms flood, block nearby road
        if value >= flood_threshold:
            self.orchestrator.impact.engine.block_area(lat, lon, radius_km=0.8)
            ws_manager.emit(
                event_type="impact_updated",
                payload={"blocked_sensor": sensor_id, "lat": lat, "lon": lon, "value": value},
            )

        return {"status": "INGESTED", "sensor_id": sensor_id, "value": value, "flood_confirmed": value >= flood_threshold}

    def update_unit_status(self, unit_id: str, new_status: str, target_id: Optional[str] = None) -> Dict[str, Any]:
        """Operator modifies operational unit status (e.g. unavailable, idle)."""
        target_unit = next((u for u in self.state["units"] if u["id"] == unit_id), None)
        if not target_unit:
            return {"error": f"Unit '{unit_id}' not found"}

        target_unit["status"] = new_status
        if target_id:
            target_unit["current_target_id"] = target_id

        # Trigger selective re-plan
        self.state["trigger_event_type"] = "unit_status_change"
        self.state["active_agents"] = []
        self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

        if self.state.get("plan_diff"):
            ws_manager.emit(event_type="plan_diff", payload=self.state["plan_diff"])
        if self.state.get("current_plan"):
            ws_manager.emit(event_type="plan_proposed", payload=self.state["current_plan"])

        return {"status": "UPDATED", "unit": target_unit}

    def block_road(self, u: Optional[str] = None, v: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, radius_km: Optional[float] = None) -> Dict[str, Any]:
        """Operator dynamically marks road or zone as flooded."""
        if u and v:
            self.orchestrator.impact.engine.block_road(u, v)
        elif lat and lon:
            self.orchestrator.impact.engine.block_area(lat, lon, radius_km=radius_km or 0.8)
        else:
            return {"error": "Must supply (u, v) edge or (lat, lon) coordinates"}

        self.state["trigger_event_type"] = "road_block"
        self.state["active_agents"] = []
        self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

        if self.state.get("plan_diff"):
            ws_manager.emit(event_type="plan_diff", payload=self.state["plan_diff"])
        return {"status": "BLOCKED", "trigger": "road_block"}

    def approve_plan(
        self,
        plan_id: str,
        signature_hex: Optional[str] = None,
        nonce: Optional[str] = None,
        timestamp: Optional[float] = None,
        commander_token: Optional[CommanderToken] = None,
        auto_sign: bool = False,
    ) -> Dict[str, Any]:
        """Cryptographically authorize plan and resume LangGraph workflow to dispatch."""
        curr_plan = self.state.get("current_plan")
        if not curr_plan or curr_plan.get("plan_id") != plan_id:
            return {"error": f"Target plan '{plan_id}' does not match current proposed plan."}

        plan_hash = self.approval_gate.compute_plan_hash(curr_plan)

        if auto_sign:
            signed = self.approval_gate.sign_approval(
                plan_id=plan_id,
                plan_hash=plan_hash,
                signing_key=self.key_manager.signing_key,
            )
            token = commander_token or CommanderToken(
                user_id="commander_certified_01",
                public_key_hex=self.key_manager.get_public_key_hex(),
            )
        else:
            if not signature_hex or not nonce or not timestamp:
                return {"error": "Missing cryptographic signature, nonce, or timestamp for approval"}
            token = commander_token
            signed = SignedApproval(
                plan_id=plan_id,
                plan_hash=plan_hash,
                commander_public_key_hex=token.public_key_hex if token else "",
                timestamp=timestamp,
                nonce=nonce,
                signature_hex=signature_hex,
            )

        # Update LangGraph checkpoint state
        self.orchestrator.graph.update_state(
            self.config,
            {
                "commander_token": token,
                "signed_approval": signed,
                "previous_approved_plan": curr_plan,
                "status": "APPROVED",
            }
        )

        # Resume execution past human_approval interrupt node into dispatch
        self.state = self.orchestrator.graph.invoke(None, config=self.config)

        if self.state.get("status") == "DISPATCHED":
            ws_manager.emit(
                event_type="plan_approved",
                payload={"plan_id": plan_id, "signature": signed.signature_hex, "nonce": signed.nonce},
            )
            ws_manager.emit(
                event_type="dispatch_issued",
                payload={"plan_id": plan_id, "assignments": curr_plan.get("assignments", [])},
            )
            return {"status": "DISPATCHED", "plan_id": plan_id, "nonce": signed.nonce}
        else:
            return {"status": "DISPATCH_BLOCKED", "error": self.state.get("dispatch_error", "Unknown dispatch block")}

    def reject_plan(self, plan_id: str, reason: str, forbidden_pairs: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """Commander rejects proposed plan with reason, triggering constraint-enforced re-plan."""
        self.state["pending_veto"] = {
            "reason": reason,
            "constraints": forbidden_pairs or [],
        }
        self.state["trigger_event_type"] = "commander_rejection"
        self.state["scheduled_agents"] = ["Resource", "Guardian", "Command"]
        self.state["veto_count"] = self.state.get("veto_count", 0) + 1
        self.state["active_agents"] = []

        # Fresh thread for rejection re-solve
        self.thread_id = f"crisis-run-{int(time.time()*1000)}"
        self.config = {"configurable": {"thread_id": self.thread_id}}

        # Re-solve under new constraints
        self.state = self.orchestrator.graph.invoke(self.state, config=self.config)

        if self.state.get("current_plan"):
            ws_manager.emit(event_type="plan_proposed", payload=self.state["current_plan"])
            ws_manager.emit(
                event_type="approval_required",
                payload={
                    "plan_id": self.state["current_plan"]["plan_id"],
                    "plan_hash": self.approval_gate.compute_plan_hash(self.state["current_plan"]),
                    "briefing": self.state.get("commander_briefing", {}),
                    "rejection_reason": reason,
                }
            )

        return {"status": "RE_PLANNED", "rejection_reason": reason, "new_plan_id": self.state.get("current_plan", {}).get("plan_id")}

    def get_snapshot(self) -> StateSnapshot:
        """Return clean Pydantic snapshot of current operational state."""
        curr_status = self.state.get("status", "INITIALIZED")
        if curr_status != "DISPATCHED" and self.state.get("current_plan"):
            curr_status = "AWAITING_COMMANDER_APPROVAL"

        return StateSnapshot(
            incidents=self.state.get("incidents", {}),
            units=self.state.get("units", []),
            hospitals=self.state.get("hospitals", []),
            verification_labels=self.state.get("verification_labels", {}),
            impact_report=self.state.get("impact_report"),
            current_plan=self.state.get("current_plan"),
            previous_approved_plan=self.state.get("previous_approved_plan"),
            plan_diff=self.state.get("plan_diff"),
            commander_briefing=self.state.get("commander_briefing"),
            pending_approvals=self.state.get("pending_approvals", []),
            message_log=self.state.get("message_log", []),
            negotiation_history=self.state.get("negotiation_history", []),
            active_agents=self.state.get("active_agents", []),
            veto_count=self.state.get("veto_count", 0),
            step_budget=self.state.get("step_budget", 20),
            status=curr_status,
            dispatch_error=self.state.get("dispatch_error"),
        )


# Global singleton
state_manager = CrisisStateManager()
