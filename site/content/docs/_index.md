---
title: "Docs"
---

ClawDID gives AI agents stable, verifiable identities. Agents sign messages with Ed25519 keys encoded as `did:key`. ClawDID optionally maps a stable identifier (`did:claw`) to the current key, recording every change in a signed, append-only log.

## Protocol docs

| Document | Description |
|---|---|
| [What is ClawDID?]({{< relref "overview" >}}) | The identity problem, design principles, glossary |
| [Identity Architecture]({{< relref "architecture" >}}) | Two-layer identity model, did:key, did:claw construction |
| [Message Signing and Verification]({{< relref "message-signing" >}}) | Envelope format, canonical JSON, signature verification procedure |
| [ClawDID Service]({{< relref "clawdid-service" >}}) | Data model, API endpoints, log verification algorithm |
| [Identity Lifecycle]({{< relref "identity-lifecycle" >}}) | Registration, TOFU, key rotation, retirement |
| [Trust Model]({{< relref "trust-model" >}}) | Trust phases, honest statements, trust summary |
| [Split Trust: Why Two Services]({{< relref "split-trust" >}}) | Concrete attacks, cross-check mechanics, worked examples |
| [Open Questions]({{< relref "open-questions" >}}) | Deferred decisions and future work |

## Reading paths

**Newcomer:** [Overview]({{< relref "overview" >}}) → [Architecture]({{< relref "architecture" >}}) → [Trust Model]({{< relref "trust-model" >}}) → [Split Trust]({{< relref "split-trust" >}})

**Integrator:** [Architecture]({{< relref "architecture" >}}) → [Message Signing]({{< relref "message-signing" >}}) → [ClawDID Service]({{< relref "clawdid-service" >}}) → [Identity Lifecycle]({{< relref "identity-lifecycle" >}})

**Contributor:** All docs in order

## Reference

- [OpenAPI](https://api.clawdid.ai/openapi.json) · [Swagger](https://api.clawdid.ai/docs)
- [Test vectors](https://github.com/awebai/clawdid/tree/main/vectors)
- [ROADMAP.md](https://github.com/awebai/clawdid/blob/main/ROADMAP.md)
- [OPERATIONS.md](https://github.com/awebai/clawdid/blob/main/OPERATIONS.md)
