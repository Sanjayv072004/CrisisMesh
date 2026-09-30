"""Ingestion Gateway: Source Authentication, Rate Limiting, Sanitization, Injection Detection."""
from backend.app.gateway.auth import HMACAuthenticator, AuthenticationError
from backend.app.gateway.rate_limiter import RateLimiter, TokenBucketRateLimiter
from backend.app.gateway.sanitizer import sanitize_text, SPOTLIGHT_START, SPOTLIGHT_END
from backend.app.gateway.injection_detector import InjectionDetector, HeuristicInjectionDetector
from backend.app.gateway.pipeline import IngestionGateway, IngestionResult

__all__ = [
    "HMACAuthenticator",
    "AuthenticationError",
    "RateLimiter",
    "TokenBucketRateLimiter",
    "sanitize_text",
    "SPOTLIGHT_START",
    "SPOTLIGHT_END",
    "InjectionDetector",
    "HeuristicInjectionDetector",
    "IngestionGateway",
    "IngestionResult",
]
