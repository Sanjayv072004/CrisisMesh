"""Prompt Injection Detector: Heuristics, Pattern Analysis & Quarantine Isolation."""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Any


class InjectionDetector(ABC):
    """Abstract interface for scanning incoming text for prompt injection attempts."""

    @abstractmethod
    def scan(self, text: str, stripped_zero_width_count: int = 0) -> Tuple[bool, str]:
        """Scan text and return (is_injection, reason)."""
        pass


class HeuristicInjectionDetector(InjectionDetector):
    """Rule-based heuristic injection scanner for LLM threat mitigation (OWASP LLM01)."""

    OVERRIDE_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|directives|prompts)",
        r"system\s+(override|prompt|directive|reset)",
        r"you\s+are\s+now\s+(an?\s+)?(in\s+developer\s+mode|jailbroken|unrestricted|god\s+mode)",
        r"send\s+(every|all|available)\s+(ambulance|boat|unit|resource|rescue)\s+to",
        r"(clear|delete|drop|wipe)\s+(active\s+)?(dispatches|database|incidents|tables)",
        r"base64\s*:\s*[A-Za-z0-9+/=]{16,}",
        r"(eval|exec|os\.system|subprocess)\s*\(",
        r"<script.*?>.*?</script>",
    ]

    def __init__(self, ml_classifier: Optional[Any] = None):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.OVERRIDE_PATTERNS]
        self.ml_classifier = ml_classifier  # Optional external ML classifier

    def scan(self, text: str, stripped_zero_width_count: int = 0) -> Tuple[bool, str]:
        """Evaluate text for instruction overrides, zero-width steganography, or jailbreaks."""
        # 1. Zero-width steganography check
        if stripped_zero_width_count > 2:
            return True, f"Steganographic prompt injection attempt detected ({stripped_zero_width_count} zero-width characters stripped)"

        # 2. Heuristic regex pattern matching
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                return True, f"Instruction override injection pattern matched: '{match.group(0)}'"

        # 3. Optional ML classifier fallback
        if self.ml_classifier:
            try:
                score = self.ml_classifier.predict(text)
                if score > 0.85:
                    return True, f"ML classifier flagged potential injection (confidence: {score:.2f})"
            except Exception:
                pass  # Gracefully skip if ML classifier fails

        return False, "Clean input text"
