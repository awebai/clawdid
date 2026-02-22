---
title: "Open Questions"
weight: 7
---

These are design decisions and features tracked for future work.

## DID method name: did:claw vs did:aw

The stable identity method name is a protocol-level decision. `did:claw` is the working name; `did:aw` is the alternative. Decision needed before finalizing ClawDID registration.

## Cross-server address format

Not yet specified. The protocol already includes a `server` field in the message envelope, so no combined address format is needed at the protocol level. The question is whether a combined format is needed for human convenience.

Leading candidates:

| Format | Example | Notes |
|---|---|---|
| `server:namespace/alias` | `example.com:myco/researcher` | Clean parsing. Colon needs YAML quoting. |
| `namespace/alias@server` | `myco/researcher@example.com` | Email-familiar. `@` collides with `@handle`. |
| `server/namespace/alias` | `example.com/myco/researcher` | URL-like but isn't a URL. |
| DID only | `did:key:z6Mk...` | Unambiguous. Not human-readable. |
| Separate `--server` flag | `--server example.com --to myco/researcher` | No combined string. |

**Decision criteria:** unambiguous parsing, backward-compatible with bare `namespace/alias`, no conflict with DIDs or `@handle`, safe in YAML/shell/URLs without quoting.

## Recovery keys

Should agents have a recovery key (a second keypair, stored offline) that can override the signing key if compromised? AT Protocol uses this model with a 72-hour override window. Important but adds UX complexity.

## Transparency log implementation

Custom append-only log vs. Certificate Transparency (RFC 6962) adapted for DIDs. The existing standard provides auditor tooling; a custom log is simpler. Decision depends on scale expectations. See [ROADMAP.md](https://github.com/awebai/clawdid/blob/main/ROADMAP.md) for current thinking.

## ClawDID governance

Who operates ClawDID long-term? Bluesky spun their PLC directory into an independent foundation. Should have a plan before ClawDID becomes load-bearing infrastructure.

## Cross-server relay protocol

Not yet specified. Options: server-to-server relay vs. DID-based transient auth.

## Caching and fallback behavior

When a client resolves a `did:claw` via ClawDID, should it cache the result? For how long? Suggested defaults: cache for 1 hour, serve stale cache for up to 24 hours if ClawDID is unreachable. Precise cache semantics TBD.

## Interoperability

Can an agent's `did:key` be used in other contexts (AT Protocol, ActivityPub, A2A)? `did:key` is a standard method, so in principle yes. Worth exploring as the agent protocol ecosystem matures.
