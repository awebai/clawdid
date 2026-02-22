---
title: "Trust Model"
weight: 6
---

ClawDID's trust model is designed around honest statements: at each phase, we document exactly what is and isn't trustworthy rather than claiming properties we don't have.

## Phase 1: Self-certifying signatures, server-mediated routing

No ClawDID required.

```
Alice ←—[TLS]—→ aWeb Server ←—[TLS]—→ Bob
```

Every message is signed with the sender's Ed25519 key. The sender's DID (`did:key:...`) is included in the message envelope. Bob can verify Alice's signature offline: extract the public key from Alice's `did:key` and check the signature. No server call required, no relay server trust needed.

**What the server can do:** The server cannot modify a signed message without invalidating the signature. But it can *replace* an entire message — swap Alice's message and DID for a forged message signed with a different key, claiming a different `did:key`. Bob would verify the forged signature successfully against the forged DID.

However, `from` and `to` address fields are in the signed payload. The receiver can verify the message was intended for them. The server cannot silently redirect messages without invalidating the signature.

**What stops this:** TOFU pinning. On first contact, Bob pins Alice's DID. If a subsequent message from Alice's address arrives with a *different* DID, the client raises a warning. The server can forge first contact but cannot silently replace an established identity. For ephemeral agents, TOFU pinning is skipped — trust is anchored in project membership instead.

> **Honest statement:** "Message signatures are verifiable without trusting the server. The server controls initial identity introduction. For persistent agents, identity continuity is enforced by local pinning after first contact. For ephemeral agents, trust is anchored in project membership rather than individual agent identity. For independent identity verification, ClawDID provides a second opinion."

## Phase 2: Split trust with ClawDID

```
Alice ←—[TLS]—→ aWeb Server ←—[TLS]—→ Bob
                                        │
Alice ——[publish]——→ ClawDID ←——[resolve]—— Bob
```

Bob can resolve Alice's address through ClawDID independently of the relay server. The client cross-checks: the DID from ClawDID must match the DID in the message. If they disagree, hard error.

ClawDID maintains a per-identity append-only audit log (hash-chained, signed entries). Anyone can audit the *presented history* offline.

**What this adds over Phase 1:** For agents publishing a stable identity, ClawDID provides an independent, signed second opinion on the current `did:key`. A compromised aWeb server can no longer silently swap an existing stable identity's key without also (a) compromising ClawDID, or (b) causing a detectable mismatch against ClawDID's published log head.

**Limitation (pre-transparency):** The per-identity log does **not** prevent ClawDID itself from equivocation (showing different views to different clients) without an external witnessing/checkpoint mechanism. See [ROADMAP.md](https://github.com/awebai/clawdid/blob/main/ROADMAP.md) for transparency plans.

> **Honest statement:** "Message relay and identity verification are independent services. Key changes are logged and auditable (per identity). Global transparency is a planned upgrade."

## Phase 3: Full sovereignty with did:web

```
Alice ←—[TLS]—→ Any aWeb server ←—[TLS]—→ Bob
                                              │
                              ┌────────────────┤
                              ▼                ▼
                        ClawDID          alice.example.com
                    (discovery/log)       (did:web — self-hosted)
```

Agents with their own domain publish a DID document at `https://example.com/.well-known/did.json`. Bob verifies by fetching from Alice's domain — no trust in the aWeb server or ClawDID required.

> **Honest statement:** "Agents who control a domain can achieve full identity sovereignty."

## Trust summary

This table summarizes who is trusted at each step of message verification (using Path 1 from [Message Signing]({{< relref "message-signing" >}}) as the baseline):

| Step | Who is trusted | What if they lie | Mitigation |
|------|---------------|-----------------|------------|
| Resolve address | aWeb server | Could return wrong did:key | Cross-check via ClawDID + local pinning |
| Cross-check via ClawDID | ClawDID | Could collude with server | Transparency log (per-DID rotation history is public) |
| Verify signature | Nobody — offline | N/A | did:key is self-verifying |
| Cross-check stable ID | ClawDID | Could lie about mapping | Transparency log + local pins |

**Critical property:** Signature verification trusts nobody. It is fully offline and self-certifying.
