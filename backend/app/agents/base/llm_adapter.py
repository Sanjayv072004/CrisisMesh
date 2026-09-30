"""LLM Adapter supporting LIVE, MOCK, and REPLAY modes with Pydantic Schema Validation."""
from __future__ import annotations
import hashlib
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Type, TypeVar, Dict, Any, Optional, Callable
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("CrisisMesh.LLMAdapter")
T = TypeVar("T", bound=BaseModel)


class LLMMode(str, Enum):
    LIVE = "LIVE"
    MOCK = "MOCK"
    REPLAY = "REPLAY"


class LLMAdapter:
    """Provider-agnostic LLM adapter enforcing structured output and offline determinism."""

    def __init__(
        self,
        mode: LLMMode = LLMMode.MOCK,
        live_provider_fn: Optional[Callable[[str, str], str]] = None,
        timeout_seconds: float = 10.0,
    ):
        self.mode = mode
        self.live_provider_fn = live_provider_fn
        self.timeout_seconds = timeout_seconds
        # Map: (agent_name, prompt_hash) -> JSON string or Dict
        self._canned_responses: Dict[Tuple[str, str], Any] = {}
        # Map: (agent_name, semantic_key) -> JSON string or Dict
        self._named_canned_responses: Dict[Tuple[str, str], Any] = {}
        # Map: trace_id -> raw JSON string
        self._replay_store: Dict[str, str] = {}

    def register_canned_response(
        self, agent_name: str, key_or_prompt: str, response: BaseModel | Dict[str, Any] | str
    ) -> None:
        """Register a canned response for MOCK mode."""
        prompt_hash = hashlib.sha256(key_or_prompt.strip().encode("utf-8")).hexdigest()[:16]
        data = response.model_dump() if isinstance(response, BaseModel) else response
        self._canned_responses[(agent_name, prompt_hash)] = data
        self._named_canned_responses[(agent_name, key_or_prompt)] = data

    def register_replay(self, trace_id: str, raw_response: str) -> None:
        """Register a recorded response for REPLAY mode."""
        self._replay_store[trace_id] = raw_response

    def load_replay_file(self, file_path: Path | str) -> None:
        """Load recorded replay responses from a JSON file."""
        p = Path(file_path)
        if p.exists():
            with open(p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._replay_store.update(data)

    def generate(
        self,
        agent_name: str,
        prompt: str,
        schema: Type[T],
        trace_id: str = "trace-default",
    ) -> T:
        """Generate structured output validated against a Pydantic schema."""
        if self.mode == LLMMode.MOCK:
            return self._generate_mock(agent_name, prompt, schema)
        elif self.mode == LLMMode.REPLAY:
            return self._generate_replay(trace_id, schema)
        elif self.mode == LLMMode.LIVE:
            return self._generate_live(agent_name, prompt, schema)
        else:
            raise ValueError(f"Unsupported LLMAdapter mode: {self.mode}")

    def _generate_mock(self, agent_name: str, prompt: str, schema: Type[T]) -> T:
        """Deterministic offline mock generation."""
        prompt_hash = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:16]

        # 1. Exact hash match
        if (agent_name, prompt_hash) in self._canned_responses:
            data = self._canned_responses[(agent_name, prompt_hash)]
            return self._validate_and_return(data, schema)

        # 2. Named substring match
        for (c_agent, c_key), data in self._named_canned_responses.items():
            if c_agent == agent_name and (c_key in prompt or prompt in c_key):
                return self._validate_and_return(data, schema)

        # 3. Fallback: Synthesize deterministic schema-valid default instance
        try:
            return schema.model_validate({})
        except ValidationError:
            seed = int(prompt_hash, 16)
            fallback_dict = self._synthesize_minimal_fields(schema, seed)
            return schema.model_validate(fallback_dict)

    def _synthesize_minimal_fields(self, schema: Type[T], seed: int) -> Dict[str, Any]:
        """Construct deterministic minimal dictionary fulfilling required fields of schema."""
        res: Dict[str, Any] = {}
        for name, field in schema.model_fields.items():
            if field.is_required():
                ann = field.annotation
                if ann is str or ann == Optional[str]:
                    res[name] = f"mock_{name}_{seed % 1000}"
                elif ann is int or ann == Optional[int]:
                    res[name] = (seed % 5) + 1
                elif ann is float or ann == Optional[float]:
                    res[name] = round((seed % 100) / 100.0, 2)
                elif ann is bool or ann == Optional[bool]:
                    res[name] = bool(seed % 2)
                elif ann is list or getattr(ann, "__origin__", None) is list:
                    res[name] = []
                elif ann is dict or getattr(ann, "__origin__", None) is dict:
                    res[name] = {}
                else:
                    res[name] = None
        return res

    def _generate_replay(self, trace_id: str, schema: Type[T]) -> T:
        """Retrieve and validate recorded replay output."""
        if trace_id not in self._replay_store:
            raise KeyError(f"No replay trace found for trace_id: '{trace_id}'")
        raw = self._replay_store[trace_id]
        return self._validate_and_return(raw, schema)

    def _generate_live(self, agent_name: str, prompt: str, schema: Type[T]) -> T:
        """Live LLM call with structured JSON validation and 1 automatic retry."""
        if not self.live_provider_fn:
            raise RuntimeError("Live provider function not configured for LIVE mode")

        json_schema = json.dumps(schema.model_json_schema())
        enforced_prompt = f"{prompt}\n\nIMPORTANT: Respond with pure JSON conforming to schema:\n{json_schema}"

        # Attempt 1
        raw_output = self.live_provider_fn(agent_name, enforced_prompt)
        try:
            return self._validate_and_return(raw_output, schema)
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"Live validation attempt 1 failed for '{agent_name}': {e}. Retrying once...")
            retry_prompt = (
                f"{enforced_prompt}\n\nYour previous output failed validation: {str(e)}.\n"
                f"Fix the JSON output to strictly match schema:\n{json_schema}"
            )
            raw_output_retry = self.live_provider_fn(agent_name, retry_prompt)
            return self._validate_and_return(raw_output_retry, schema)

    def _validate_and_return(self, data: Any, schema: Type[T]) -> T:
        if isinstance(data, schema):
            return data
        if isinstance(data, dict):
            return schema.model_validate(data)
        if isinstance(data, str):
            clean_str = data.strip()
            if clean_str.startswith("```"):
                lines = clean_str.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                clean_str = "\n".join(lines).strip()
            return schema.model_validate_json(clean_str)
        raise ValueError(f"Cannot validate data of type {type(data)} against schema {schema.__name__}")
