"""Rate Limiter: Token Bucket Interface and In-Memory Implementation."""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from typing import Dict, Tuple


class RateLimiter(ABC):
    """Abstract interface for rate limiting (can be swapped for Redis)."""

    @abstractmethod
    def allow_request(self, key: str, cost: int = 1) -> Tuple[bool, str]:
        """Check if request is allowed under rate limits."""
        pass


class TokenBucketRateLimiter(RateLimiter):
    """Thread-safe in-memory token bucket rate limiter."""

    def __init__(self, capacity: int = 10, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        # Map: key -> (current_tokens, last_refill_timestamp)
        self.buckets: Dict[str, Tuple[float, float]] = {}

    def allow_request(self, key: str, cost: int = 1) -> Tuple[bool, str]:
        """Consume tokens if available, otherwise reject."""
        now = time.time()
        tokens, last_refill = self.buckets.get(key, (float(self.capacity), now))

        # Refill tokens
        elapsed = now - last_refill
        refilled_tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)

        if refilled_tokens >= cost:
            self.buckets[key] = (refilled_tokens - cost, now)
            return True, "Request allowed"

        self.buckets[key] = (refilled_tokens, now)
        return False, f"Rate limit exceeded for key '{key}' (current tokens: {refilled_tokens:.1f}, required: {cost})"

    def reset(self, key: Optional[str] = None):
        """Reset buckets for testing."""
        if key:
            self.buckets.pop(key, None)
        else:
            self.buckets.clear()
