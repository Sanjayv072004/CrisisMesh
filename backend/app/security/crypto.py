"""Cryptographic Approvals: Ed25519 Digital Signatures, Nonce Replay Defense, and Plan Hash Binding."""
from __future__ import annotations
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple, Set, Any
import nacl.signing
import nacl.encoding
from pydantic import BaseModel, Field

KEYS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / ".keys"


class SignedApproval(BaseModel):
    """Cryptographically signed approval payload."""
    plan_id: str
    plan_hash: str
    commander_public_key_hex: str
    timestamp: float
    nonce: str
    signature_hex: str


class CommanderKeyManager:
    """Manages Ed25519 commander signing keys, persisting outside git."""

    def __init__(self, key_path: Optional[Path] = None):
        self.key_path = key_path or (KEYS_DIR / "commander_ed25519.key")
        self.signing_key, self.verify_key = self._load_or_generate()

    def _load_or_generate(self) -> Tuple[nacl.signing.SigningKey, nacl.signing.VerifyKey]:
        if self.key_path.exists():
            try:
                with open(self.key_path, "rb") as f:
                    seed = f.read()
                    sk = nacl.signing.SigningKey(seed)
                    return sk, sk.verify_key
            except Exception:
                pass

        # Generate fresh Ed25519 keypair
        sk = nacl.signing.SigningKey.generate()
        try:
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_path, "wb") as f:
                f.write(sk.encode())
        except Exception:
            pass
        return sk, sk.verify_key

    def get_public_key_hex(self) -> str:
        return self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")


class ApprovalGate:
    """Enforces cryptographic verification of commander authorization before fleet dispatch."""

    def __init__(self, max_validity_seconds: float = 900.0):
        self.max_validity_seconds = max_validity_seconds
        # Replay protection store: set of observed nonces
        self._consumed_nonces: Set[str] = set()

    @staticmethod
    def compute_plan_hash(plan_dict_or_obj: Any) -> str:
        """Compute deterministic SHA-256 canonical hash of a Plan."""
        if hasattr(plan_dict_or_obj, "model_dump"):
            d = plan_dict_or_obj.model_dump()
        elif isinstance(plan_dict_or_obj, dict):
            d = dict(plan_dict_or_obj)
        else:
            d = {"data": str(plan_dict_or_obj)}

        # Strip variable timestamps / statuses to bind structure
        normalized = {
            "assignments": d.get("assignments", []),
            "unserved_incidents": d.get("unserved_incidents", []),
            "cost_breakdown": d.get("cost_breakdown", {}),
        }
        canonical_json = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def sign_approval(
        self, plan_id: str, plan_hash: str, signing_key: nacl.signing.SigningKey
    ) -> SignedApproval:
        """Sign a plan approval binding plan_id, plan_hash, current timestamp, and a random nonce."""
        ts = time.time()
        nonce = str(uuid.uuid4())
        message_bytes = f"{plan_id}:{plan_hash}:{ts}:{nonce}".encode("utf-8")
        signed = signing_key.sign(message_bytes)
        sig_hex = signed.signature.hex()
        pub_hex = signing_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")

        return SignedApproval(
            plan_id=plan_id,
            plan_hash=plan_hash,
            commander_public_key_hex=pub_hex,
            timestamp=ts,
            nonce=nonce,
            signature_hex=sig_hex
        )

    def verify_before_dispatch(
        self,
        approval: SignedApproval,
        expected_plan_hash: str,
        expected_commander_pubkey_hex: str,
    ) -> Tuple[bool, str]:
        """Verify Ed25519 signature, plan-hash integrity, timestamp freshness, and nonce replay."""
        # 1. Missing signature
        if not approval.signature_hex:
            return False, "Missing signature in approval payload"

        # 2. Wrong signer check
        if approval.commander_public_key_hex != expected_commander_pubkey_hex:
            return False, f"Signature public key ({approval.commander_public_key_hex[:8]}...) does not match authorized Commander key ({expected_commander_pubkey_hex[:8]}...)"

        # 3. Altered plan check (Hash mismatch)
        if approval.plan_hash != expected_plan_hash:
            return False, f"Plan hash mismatch: approval bound to {approval.plan_hash[:8]}..., but target plan hash is {expected_plan_hash[:8]}... (Altered Plan Attack)"

        # 4. Timestamp expiry check
        now = time.time()
        elapsed = now - approval.timestamp
        if elapsed > self.max_validity_seconds:
            return False, f"Approval signature has expired ({elapsed:.1f}s ago; max allowed: {self.max_validity_seconds}s)"
        if elapsed < -60.0:
            return False, "Approval timestamp is in the future"

        # 5. Nonce replay check
        if approval.nonce in self._consumed_nonces:
            return False, f"Replay attack detected: Nonce '{approval.nonce}' has already been consumed"

        # 6. Cryptographic Ed25519 verification
        try:
            verify_key = nacl.signing.VerifyKey(
                approval.commander_public_key_hex, encoder=nacl.encoding.HexEncoder
            )
            message_bytes = f"{approval.plan_id}:{approval.plan_hash}:{approval.timestamp}:{approval.nonce}".encode("utf-8")
            sig_bytes = bytes.fromhex(approval.signature_hex)
            verify_key.verify(message_bytes, sig_bytes)
        except Exception as e:
            return False, f"Cryptographic verification failed: {e} (Forged Signature Attack)"

        # Consume nonce to prevent replay
        self._consumed_nonces.add(approval.nonce)
        return True, "Valid signed approval verified"
