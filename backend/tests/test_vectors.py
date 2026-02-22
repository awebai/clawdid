from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from nacl.signing import SigningKey

from clawdid.did import did_claw_from_public_key, public_key_from_did_key
from clawdid.signing import canonical_json_bytes, verify_did_key_signature


def _repo_root() -> Path:
    # backend/tests/... -> backend -> repo root
    return Path(__file__).resolve().parents[2]


def _b64_nopad(data: bytes) -> str:
    return base64.b64encode(data).rstrip(b"=").decode("ascii")


def test_message_signing_vectors():
    vectors_path = _repo_root() / "vectors" / "message-signing-v1.json"
    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))

    for vec in vectors:
        seed = bytes.fromhex(vec["signing_seed_hex"])
        sk = SigningKey(seed)

        did_key = vec["signing_did_key"]
        assert public_key_from_did_key(did_key) == bytes(sk.verify_key)

        payload = canonical_json_bytes(vec["message"])
        assert payload.decode("utf-8") == vec["canonical_payload"]

        sig_b64 = _b64_nopad(sk.sign(payload).signature)
        assert sig_b64 == vec["signature_b64"]

        verify_did_key_signature(
            did_key=did_key, payload=payload, signature_b64=sig_b64
        )


def test_stable_id_vectors():
    vectors_path = _repo_root() / "vectors" / "stable-id-v1.json"
    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))

    for vec in vectors:
        did_key = vec["did_key"]
        public_key = public_key_from_did_key(did_key)
        assert public_key.hex() == vec["public_key_hex"]

        assert (
            did_claw_from_public_key(public_key, method="claw") == vec["stable_id_claw"]
        )
        assert did_claw_from_public_key(public_key, method="aw") == vec["stable_id_aw"]


def test_clawdid_log_vectors():
    vectors_path = _repo_root() / "vectors" / "clawdid-log-v1.json"
    doc = json.loads(vectors_path.read_text(encoding="utf-8"))

    sk_initial = SigningKey(bytes.fromhex(doc["key_seeds"]["initial_seed_hex"]))

    previous_entry_hash: str | None = None
    for entry in doc["entries"]:
        entry_payload = entry["entry_payload"]

        # state_hash is defined as sha256(canonical_json(mapping_state))
        mapping = doc["mapping"]
        state_payload = canonical_json_bytes(
            {
                "address": mapping["address"],
                "current_did_key": entry_payload["new_did_key"],
                "did_claw": mapping["did_claw"],
                "handle": mapping["handle"],
                "server": mapping["server"],
            }
        )
        assert hashlib.sha256(state_payload).hexdigest() == entry["state_hash"]
        assert entry_payload["state_hash"] == entry["state_hash"]

        # canonical log entry payload + entry_hash
        canonical_entry = canonical_json_bytes(entry_payload)
        assert canonical_entry.decode("utf-8") == entry["canonical_entry_payload"]
        computed_entry_hash = hashlib.sha256(canonical_entry).hexdigest()
        assert computed_entry_hash == entry["entry_hash"]

        # chain
        if entry_payload["seq"] == 1:
            assert entry_payload["prev_entry_hash"] is None
        else:
            assert entry_payload["prev_entry_hash"] == previous_entry_hash

        # signature must verify against authorized_by did:key
        sig_b64 = _b64_nopad(sk_initial.sign(canonical_entry).signature)
        assert sig_b64 == entry["signature_b64"]
        verify_did_key_signature(
            did_key=entry_payload["authorized_by"],
            payload=canonical_entry,
            signature_b64=sig_b64,
        )

        previous_entry_hash = computed_entry_hash
