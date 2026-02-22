from __future__ import annotations

import hashlib

import base58

_DID_KEY_PREFIX = "did:key:z"
_DID_CLAW_PREFIX = "did:claw:"
_DID_AW_PREFIX = "did:aw:"

_MULTICODEC_ED25519 = b"\xed\x01"


def public_key_from_did_key(did_key: str) -> bytes:
    if not did_key.startswith(_DID_KEY_PREFIX):
        raise ValueError("did_key must start with did:key:z")
    encoded = did_key[len(_DID_KEY_PREFIX) :]
    decoded = base58.b58decode(encoded)
    if len(decoded) != 34:
        raise ValueError("did:key payload must be 34 bytes (0xed01 + 32 byte pubkey)")
    if decoded[:2] != _MULTICODEC_ED25519:
        raise ValueError("did:key multicodec prefix must be 0xed01 (Ed25519)")
    return decoded[2:]


def did_claw_from_public_key(public_key: bytes, *, method: str = "claw") -> str:
    if len(public_key) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")
    digest = hashlib.sha256(public_key).digest()[:20]
    suffix = base58.b58encode(digest).decode("ascii")
    if method == "claw":
        return _DID_CLAW_PREFIX + suffix
    if method == "aw":
        return _DID_AW_PREFIX + suffix
    raise ValueError("method must be 'claw' or 'aw'")


def validate_stable_id(stable_id: str) -> None:
    if stable_id.startswith(_DID_CLAW_PREFIX) or stable_id.startswith(_DID_AW_PREFIX):
        return
    raise ValueError("stable_id must start with did:claw: or did:aw:")
