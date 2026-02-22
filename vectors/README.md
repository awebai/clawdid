# Protocol conformance vectors

This directory publishes **deterministic conformance vectors** for the aWeb identity and ClaWDID
protocol rules defined in `sot.md` and `sot-2026-02-22-addendum-v2.md`.

These vectors exist to prevent subtle cross-language drift (Python ↔ Go) in:
- Canonical JSON serialization
- Signature base64 encoding
- `did:key` ↔ public key parsing
- Stable ID derivation (`did:claw:` / `did:aw:`)
- ClaWDID audit-log entry hashing + signing

## Files

- `message-signing-v1.json`
  - Canonical message payload (UTF-8 bytes)
  - Expected Ed25519 signature (standard base64, **no padding**)
  - Includes variants with and without stable ID fields

- `clawdid-log-v1.json`
  - Canonical ClaWDID log entry payload
  - Expected `entry_hash` (sha256 hex)
  - Expected Ed25519 signature (standard base64, **no padding**)

- `stable-id-v1.json`
  - `did:key` → stable ID derivation vectors

- `rotation-announcements-v1.json`
  - Canonical rotation-announcement payloads (single link + chaining)
  - Expected Ed25519 signatures (standard base64, **no padding**)

## Encoding notes

- **Canonical JSON:** lexicographic key sort, compact separators, literal UTF-8 (no `\uXXXX` escapes).
- **Signatures:** Ed25519 signature bytes encoded as **standard** base64 (RFC 4648), no `=` padding.

## Validation

The backend test suite validates these vectors:

```bash
cd backend
make test
```
