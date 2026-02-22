from __future__ import annotations

import base64
import json

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from clawdid.did import public_key_from_did_key


def canonical_json_bytes(fields: dict) -> bytes:
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def verify_did_key_signature(
    *, did_key: str, payload: bytes, signature_b64: str
) -> None:
    public_key = public_key_from_did_key(did_key)

    padded = signature_b64 + "=" * (-len(signature_b64) % 4)
    sig_bytes = base64.b64decode(padded, validate=True)

    try:
        VerifyKey(public_key).verify(payload, sig_bytes)
    except BadSignatureError as e:
        raise ValueError("invalid signature") from e
