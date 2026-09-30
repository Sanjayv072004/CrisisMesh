"""Source Authentication with HMAC-SHA256 for Registered Feeds."""
from __future__ import annotations
import hmac
import hashlib
from typing import Dict, Optional, Tuple


class AuthenticationError(Exception):
    """Raised when an authenticated source fails HMAC validation."""
    pass


class HMACAuthenticator:
    """Authenticates registered sensor and hospital data feeds using HMAC-SHA256."""

    def __init__(self, key_registry: Optional[Dict[str, str]] = None):
        # Default dev secret keys for registered telemetry feeds
        self.key_registry: Dict[str, str] = key_registry or {
            "gauge_silkboard_01": "secret_key_gauge_silkboard",
            "gauge_bellandur_lake_02": "secret_key_bellandur_telemetry",
            "rain_hsr_01": "secret_key_rain_sensor_hsr",
            "traffic_police_hq": "secret_key_traffic_police_feed",
            "bbmp_control_room": "secret_key_bbmp_feed",
        }

    def register_source(self, source_id: str, secret: str) -> None:
        """Register a new source with its shared HMAC secret key."""
        self.key_registry[source_id] = secret

    def is_registered(self, source_id: str) -> bool:
        """Check if source is registered for HMAC authentication."""
        return source_id in self.key_registry

    def compute_signature(self, source_id: str, data_bytes: bytes) -> str:
        """Compute expected HMAC-SHA256 hex digest for payload."""
        if source_id not in self.key_registry:
            raise KeyError(f"Source '{source_id}' is not registered in HMAC registry")
        secret = self.key_registry[source_id].encode("utf-8")
        return hmac.new(secret, data_bytes, hashlib.sha256).hexdigest()

    def verify(self, source_id: str, data_bytes: bytes, signature_hex: Optional[str]) -> Tuple[bool, str]:
        """Verify HMAC signature for a registered source.
        
        Returns:
            (is_valid, reason)
        """
        if not self.is_registered(source_id):
            # Unregistered citizen reports are accepted as untrusted
            return True, "Unregistered citizen source (accepted as untrusted)"

        if not signature_hex:
            return False, f"Registered source '{source_id}' submitted data without required HMAC signature"

        expected_sig = self.compute_signature(source_id, data_bytes)
        if hmac.compare_digest(expected_sig, signature_hex):
            return True, "HMAC signature verified"

        return False, f"Invalid HMAC signature for registered source '{source_id}'"
