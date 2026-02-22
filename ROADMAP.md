# clawdid roadmap

This project is intentionally small at launch: a stable-ID mapping API plus an append-only, self-verifying
per-identity audit log.

## What v0.1 (launch) guarantees

- `did:key` remains the cryptographic identity layer (offline signature verification, zero network calls).
- `did:claw` is an optional stable identifier that maps to the current `did:key`.
- ClawDID provides:
  - Point lookups (`/did/{did_claw}/key`) with a signed log-head commitment
  - Full records (`/did/{did_claw}/full`) behind authentication
  - Per-identity mutation history (`/did/{did_claw}/log`)
- The audit log is self-verifying (hash chain + Ed25519 signatures over canonical payloads).

## Known limitations (explicitly not solved at launch)

- **No global transparency yet.** Without witnesses/checkpoints, ClawDID could theoretically equivocate
  (serve different histories/log heads to different verifiers). The per-identity log is tamper-evident,
  but not globally consistent by construction.
- **TOFU limits remain.** First-contact identity introduction still requires an honest channel or an
  out-of-band trust anchor; stable identity helps continuity, not bootstrapping.

## Planned work (post-launch)

### 1) Transparency + equivocation resistance

Goal: make equivocation detectable by default.

- Signed log checkpoints (e.g. daily) over the set of `(did_claw, seq, entry_hash)` heads
- Merkle tree / signed tree head (STH) style publication
- Witnessing:
  - Independent witness services that mirror checkpoints
  - Client gossip: `aw` shares/compares checkpoint heads opportunistically
- Verifier UX: clear warnings when checkpoints diverge or are missing

### 2) Abuse resistance + rate limiting

- Hardened rate limiting policy (per-IP, per-did:claw, per-route)
- Backpressure / caching for `/key`
- Operational alerts for abusive patterns

### 3) Client + server integrations

- `aw` resolver: optional ClawDID cross-check when `from_stable_id` is present
- `aweb` publication hooks: publish stable identities + rotation/server-migration updates
- `claweb` UI: show stable identity + audit history, explain trust levels honestly

### 4) Operations hardening

- Structured logs + metrics for latency, error rates, and DB pool saturation
- Safer migrations and rollback guidance
- Disaster recovery + backups playbook

## How to help

- Read `sot.md` and `sot-2026-02-22-addendum-v2.md` and file issues for unclear or underspecified sections.
- Add interoperability tests/vectors (Go + Python) for any protocol change.
