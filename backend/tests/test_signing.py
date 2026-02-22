from __future__ import annotations

import base64

from nacl.signing import SigningKey

from clawdid.signing import canonical_json_bytes, verify_did_key_signature


def test_verify_did_key_signature_ok():
    sk = SigningKey.generate()
    did_key = "did:key:z" + __import__("base58").b58encode(
        b"\xed\x01" + bytes(sk.verify_key)
    ).decode("ascii")
    payload = canonical_json_bytes({"a": 1, "b": "x"})
    sig = base64.b64encode(sk.sign(payload).signature).rstrip(b"=").decode("ascii")
    verify_did_key_signature(did_key=did_key, payload=payload, signature_b64=sig)
