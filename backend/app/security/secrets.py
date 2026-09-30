"""Secrets Management: Strict Environment Validation and Safe Mock Fallbacks."""
from __future__ import annotations
import os
from typing import Optional, Dict


class SecretsConfig:
    """Manages sensitive runtime credentials with strict live-mode validation."""

    def __init__(self, mode: Optional[str] = None):
        self.mode = (mode or os.getenv("CRISISMESH_MODE", "MOCK")).upper()
        self._secrets: Dict[str, str] = {}
        self._load_and_validate()

    def _load_and_validate(self) -> None:
        required_in_live = [
            "GEMINI_API_KEY",
            "CRISISMESH_HMAC_SECRET",
        ]

        if self.mode == "LIVE":
            missing = [k for k in required_in_live if not os.getenv(k)]
            if missing:
                raise RuntimeError(
                    f"CRITICAL SECURITY CONFIGURATION ERROR: Missing required secrets in LIVE mode: {', '.join(missing)}. "
                    f"Refusing to boot insecurely."
                )
            self._secrets["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"]
            self._secrets["CRISISMESH_HMAC_SECRET"] = os.environ["CRISISMESH_HMAC_SECRET"]
        else:
            # Deterministic, safe mock secrets for offline testing and evaluation
            self._secrets["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "mock-gemini-key-live000000000000")
            self._secrets["CRISISMESH_HMAC_SECRET"] = os.getenv(
                "CRISISMESH_HMAC_SECRET", "crisismesh-sensor-hmac-shared-key-2026"
            )

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._secrets.get(key, os.getenv(key, default))

    @property
    def is_live(self) -> bool:
        return self.mode == "LIVE"


# Global singleton
secrets_config = SecretsConfig()
