from __future__ import annotations

import base58

from clawdid.did import (
    did_claw_from_public_key,
    public_key_from_did_key,
    validate_stable_id,
)


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


def test_validate_stable_id_rejects_empty_suffix():
    try:
        validate_stable_id("did:claw:")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validate_stable_id_rejects_non_base58():
    try:
        validate_stable_id("did:claw:!!!!")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validate_stable_id_rejects_wrong_length_decoding():
    # base58 encoding of 1 byte will decode to 1 byte, not 20.
    short = "did:claw:" + base58.b58encode(b"\x01").decode("ascii")
    try:
        validate_stable_id(short)
        assert False, "expected ValueError"
    except ValueError:
        pass
