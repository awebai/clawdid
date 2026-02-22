from __future__ import annotations

import base58

from clawdid.did import did_claw_from_public_key, public_key_from_did_key


def test_public_key_from_did_key_roundtrip():
    pub = b"\x11" * 32
    did_key = "did:key:z" + base58.b58encode(b"\xed\x01" + pub).decode("ascii")
    assert public_key_from_did_key(did_key) == pub


def test_did_claw_derivation_deterministic():
    pub = b"\x22" * 32
    a = did_claw_from_public_key(pub, method="claw")
    b = did_claw_from_public_key(pub, method="claw")
    assert a == b
    assert a.startswith("did:claw:")


def test_did_aw_derivation_prefix():
    pub = b"\x33" * 32
    did = did_claw_from_public_key(pub, method="aw")
    assert did.startswith("did:aw:")
