"""Tamper-Evident Hash-Chained Audit Log."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """Immutable entry in the tamper-evident cryptographic hash chain."""
    index: int
    timestamp: float
    event_type: str
    actor: str
    payload_hash: str
    prev_hash: str
    hash: str
    signature: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class AuditChain:
    """Tamper-evident append-only log using SHA-256 hash chaining."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path
        self._entries: List[AuditEntry] = []
        if self.log_path and self.log_path.exists():
            self._load_from_file()
        else:
            self._init_genesis()

    @staticmethod
    def compute_payload_hash(payload: Any) -> str:
        """Deterministically hash arbitrary payload via canonical JSON."""
        if hasattr(payload, "model_dump"):
            data = payload.model_dump(mode="json")
        elif isinstance(payload, dict):
            data = payload
        elif isinstance(payload, (list, tuple)):
            data = list(payload)
        else:
            data = {"value": str(payload)}
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_entry_hash(
        prev_hash: str,
        index: int,
        timestamp: float,
        event_type: str,
        actor: str,
        payload_hash: str,
    ) -> str:
        """Deterministic block hash over all header fields."""
        raw = f"{prev_hash}:{index}:{timestamp:.6f}:{event_type}:{actor}:{payload_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _init_genesis(self) -> None:
        """Initialize genesis block index 0 with 64 zero-byte prev_hash."""
        ts = 0.0
        payload_hash = hashlib.sha256(b"CRISISMESH_GENESIS").hexdigest()
        prev_hash = "0" * 64
        entry_hash = self.compute_entry_hash(
            prev_hash=prev_hash,
            index=0,
            timestamp=ts,
            event_type="GENESIS",
            actor="SYSTEM",
            payload_hash=payload_hash,
        )
        genesis = AuditEntry(
            index=0,
            timestamp=ts,
            event_type="GENESIS",
            actor="SYSTEM",
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            hash=entry_hash,
            payload={"system": "CrisisMesh", "protocol": "v1.0"},
        )
        self._entries.append(genesis)
        self._persist_entry(genesis)

    def append(
        self,
        event_type: str,
        actor: str,
        payload: Any,
        signature: Optional[str] = None,
    ) -> AuditEntry:
        """Append a new event block to the chain."""
        last_entry = self._entries[-1]
        index = len(self._entries)
        ts = time.time()
        payload_hash = self.compute_payload_hash(payload)
        prev_hash = last_entry.hash

        entry_hash = self.compute_entry_hash(
            prev_hash=prev_hash,
            index=index,
            timestamp=ts,
            event_type=event_type,
            actor=actor,
            payload_hash=payload_hash,
        )

        entry_payload = (
            payload.model_dump(mode="json")
            if hasattr(payload, "model_dump")
            else (payload if isinstance(payload, dict) else {"content": str(payload)})
        )

        entry = AuditEntry(
            index=index,
            timestamp=ts,
            event_type=event_type,
            actor=actor,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            hash=entry_hash,
            signature=signature,
            payload=entry_payload,
        )

        self._entries.append(entry)
        self._persist_entry(entry)
        return entry

    def verify_chain(self) -> Tuple[bool, Optional[int]]:
        """Verify complete cryptographic chain integrity.

        Returns:
            (True, None) if the chain is fully intact.
            (False, broken_index) where broken_index is the 0-based index of the first corrupted entry.
        """
        if not self._entries:
            return False, 0

        # Verify genesis block
        genesis = self._entries[0]
        if genesis.index != 0 or genesis.prev_hash != ("0" * 64):
            return False, 0
        expected_gen_hash = self.compute_entry_hash(
            prev_hash=genesis.prev_hash,
            index=0,
            timestamp=genesis.timestamp,
            event_type=genesis.event_type,
            actor=genesis.actor,
            payload_hash=genesis.payload_hash,
        )
        if genesis.hash != expected_gen_hash:
            return False, 0

        # Verify consecutive blocks
        for i in range(1, len(self._entries)):
            curr = self._entries[i]
            prev = self._entries[i - 1]

            if curr.index != i:
                return False, i

            # 1. Broken link check: current prev_hash must match predecessor hash
            if curr.prev_hash != prev.hash:
                return False, i

            # 2. Payload tampering check: recomputed payload hash must match
            if curr.payload is not None:
                recomputed_payload_hash = self.compute_payload_hash(curr.payload)
                if curr.payload_hash != recomputed_payload_hash:
                    return False, i

            # 3. Block tampering check: recomputed entry hash must match
            expected_hash = self.compute_entry_hash(
                prev_hash=curr.prev_hash,
                index=curr.index,
                timestamp=curr.timestamp,
                event_type=curr.event_type,
                actor=curr.actor,
                payload_hash=curr.payload_hash,
            )
            if curr.hash != expected_hash:
                return False, i

        return True, None

    def _persist_entry(self, entry: AuditEntry) -> None:
        if self.log_path:
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(entry.model_dump_json() + "\n")
            except Exception as e:
                print(f"[AuditChain] Persistence error: {e}")

    def _load_from_file(self) -> None:
        self._entries.clear()
        if not self.log_path or not self.log_path.exists():
            self._init_genesis()
            return
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self._entries.append(AuditEntry.model_validate_json(line))
        if not self._entries:
            self._init_genesis()

    def get_entries(self) -> List[AuditEntry]:
        """Return shallow copy of all audit entries."""
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
