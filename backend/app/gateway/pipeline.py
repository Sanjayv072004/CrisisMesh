"""Ingestion Gateway Pipeline: Auth, Rate Limiting, Sanitization, and Injection Defense."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from backend.app.gateway.auth import HMACAuthenticator
from backend.app.gateway.rate_limiter import TokenBucketRateLimiter
from backend.app.gateway.sanitizer import sanitize_text
from backend.app.gateway.injection_detector import HeuristicInjectionDetector
from backend.app.models.schemas import Report, SecurityEvent


class IngestionResult:
    """Outcome of passing an untrusted payload through the Ingestion Gateway."""
    def __init__(
        self,
        report: Optional[Report],
        spotlit_text: str,
        is_quarantined: bool = False,
        quarantine_reason: str = "",
        is_rate_limited: bool = False,
        is_auth_rejected: bool = False,
        security_events: Optional[List[SecurityEvent]] = None,
    ):
        self.report = report
        self.spotlit_text = spotlit_text
        self.is_quarantined = is_quarantined
        self.quarantine_reason = quarantine_reason
        self.is_rate_limited = is_rate_limited
        self.is_auth_rejected = is_auth_rejected
        self.security_events = security_events or []


class IngestionGateway:
    """Full-featured Ingestion Gateway enforcing front-door security invariants."""

    def __init__(
        self,
        authenticator: Optional[HMACAuthenticator] = None,
        rate_limiter: Optional[TokenBucketRateLimiter] = None,
        detector: Optional[HeuristicInjectionDetector] = None,
    ):
        self.auth = authenticator or HMACAuthenticator()
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(capacity=10, refill_rate_per_sec=2.0)
        self.detector = detector or HeuristicInjectionDetector()

    def ingest_report(
        self,
        raw_text: str,
        source_id: str,
        lat: float,
        lon: float,
        ip_address: str = "127.0.0.1",
        signature_hex: Optional[str] = None,
        report_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """Process an incoming civilian or agency report through all security gates."""
        security_events: List[SecurityEvent] = []

        # 1. Source Authentication (HMAC for registered feeds)
        raw_bytes = raw_text.encode("utf-8")
        is_auth, auth_msg = self.auth.verify(source_id, raw_bytes, signature_hex)
        if not is_auth:
            event = SecurityEvent(
                event_type="spoofed_source_hmac",
                severity="HIGH",
                agent_name="IngestionGateway",
                description=f"Rejected payload from '{source_id}': {auth_msg}",
                metadata={"source_id": source_id, "signature": signature_hex}
            )
            security_events.append(event)
            return IngestionResult(
                report=None,
                spotlit_text="",
                is_auth_rejected=True,
                quarantine_reason=auth_msg,
                security_events=security_events
            )

        # 2. Rate Limiting (Token Bucket per IP and per Source)
        key_source = f"src:{source_id}"
        key_ip = f"ip:{ip_address}"
        allowed_src, src_msg = self.rate_limiter.allow_request(key_source)
        allowed_ip, ip_msg = self.rate_limiter.allow_request(key_ip)

        if not allowed_src or not allowed_ip:
            event = SecurityEvent(
                event_type="rate_limit_exceeded",
                severity="MEDIUM",
                agent_name="IngestionGateway",
                description=src_msg if not allowed_src else ip_msg,
                metadata={"source_id": source_id, "ip": ip_address}
            )
            security_events.append(event)
            return IngestionResult(
                report=None,
                spotlit_text="",
                is_rate_limited=True,
                quarantine_reason="Rate limit burst exceeded",
                security_events=security_events
            )

        # 3. Sanitization & Zero-Width Stripping & Spotlighting Delimiters
        clean_text, spotlit_text, stripped_zero = sanitize_text(raw_text)

        # 4. Prompt Injection Scan
        is_injection, injection_reason = self.detector.scan(clean_text, stripped_zero_width_count=stripped_zero)
        is_quarantined = is_injection
        quarantine_reason = injection_reason if is_injection else ""

        if is_injection:
            event = SecurityEvent(
                event_type="prompt_injection_detected",
                severity="HIGH",
                agent_name="IngestionGateway",
                description=f"Quarantined malicious report: {injection_reason}",
                metadata={"source_id": source_id, "stripped_zero_chars": stripped_zero}
            )
            security_events.append(event)

        meta = dict(metadata or {})
        meta["is_quarantined"] = is_quarantined
        meta["is_adversarial"] = is_injection
        meta["quarantine_reason"] = quarantine_reason
        meta["is_authenticated_source"] = self.auth.is_registered(source_id)
        if is_injection:
            meta["confidence"] = 0.05

        report = Report(
            id=report_id or f"rep_{source_id}_{int(lat*1000)}",
            text=clean_text,
            source_id=source_id,
            lat=lat,
            lon=lon,
            metadata=meta
        )

        return IngestionResult(
            report=report,
            spotlit_text=spotlit_text,
            is_quarantined=is_quarantined,
            quarantine_reason=quarantine_reason,
            security_events=security_events
        )
