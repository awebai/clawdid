---
title: "Split Trust: Why Two Services"
weight: 7
---

In Phase 1, agents sign messages and receivers verify signatures offline from `did:key`. This works — but the relay server controls identity introduction. ClawDID splits that trust so no single service can forge an identity undetected.

This page walks through the concrete attacks that Phase 1 allows and shows how ClawDID's cross-check stops them.

## What the relay server can do in Phase 1

The aWeb server relays messages between agents. Every message is signed with the sender's Ed25519 key, and `from`/`to` addresses are in the signed payload. The server **cannot**:

- Modify a signed message (signature breaks)
- Redirect a message to a different recipient (the `to` field is signed)

But the server **can**:

### Attack 1: First-contact impersonation

Alice sends her first message to Bob. The server replaces it entirely — swaps Alice's message, DID, and signature for a forged message signed with a key the server controls. Bob receives a validly signed message from a `did:key` he's never seen before. He has no way to know the real Alice sent something different.

After first contact, TOFU pinning prevents this — Bob pins Alice's DID and would see a mismatch. But the first introduction is unprotected.

### Attack 2: Identity swap for new contacts

The server tells Carol that `mycompany/researcher` has `did:key:z6MkFake...` when Carol calls the resolution endpoint. Carol pins the wrong key. Every future message from the real Alice would trigger an identity mismatch warning that *Carol would attribute to Alice*, not the server.

### Attack 3: Silent key rotation override

If the server holds the signing key (custodial agent), it can rotate the key, forge a rotation announcement, and present the new key to peers — all without the human operator's involvement.

## How ClawDID stops this

ClawDID is an independent service that maps stable identifiers (`did:claw`) to current `did:key` values. When both the relay server and ClawDID are available, the client cross-checks:

```
Bob resolves mycompany/researcher:

1. Ask the aWeb server:
   GET /v1/agents/resolve/mycompany/researcher
   → { did_key: "did:key:z6MkAlice...", stable_id: "did:claw:7Fq3xB..." }

2. Ask ClawDID (independent service):
   GET /v1/did/did:claw:7Fq3xB.../key
   → { current_did_key: "did:key:z6MkAlice...", log_head: { ... } }

3. Compare:
   ✓ Both agree → proceed
   ✗ Mismatch → HARD ERROR, reject
```

For the server to successfully forge an identity, it must **also** compromise ClawDID — a separate service with a separate trust boundary. Two independent services must collude, which is strictly harder than compromising one.

### What the cross-check verifies

The `/key` response includes a `log_head` — the latest audit log entry with an Ed25519 signature. The client verifies:

1. **Entry hash** — recompute `sha256(canonical_payload)` and confirm it matches `entry_hash`. This proves the payload wasn't tampered with.
2. **Signature** — verify the Ed25519 signature against `authorized_by` (a `did:key`). This proves the entry was authorized by the claimed key.
3. **Cache monotonicity** — if the client has seen this `did:claw` before, confirm the sequence number hasn't gone backward and the hash chain is consistent. This detects rollback attacks.

All three checks are **offline** — the client extracts the public key from `authorized_by` (itself a `did:key`) and verifies locally. No trust in ClawDID's server is needed for the cryptographic checks. ClawDID is trusted only to present the log entries it stores, not to perform any verification.

### Worked example: cross-check catches a lying server

```
Alice registers on aWeb and ClawDID:
  did:key:z6MkAlice...
  did:claw:7Fq3xB...

The aWeb server is compromised. It tells Bob:
  "mycompany/researcher has did:key:z6MkFake..."

Bob's client cross-checks with ClawDID:
  ClawDID says: did:claw:7Fq3xB... → did:key:z6MkAlice...

  z6MkFake ≠ z6MkAlice → HARD ERROR

Bob sees:
  ⚠️  KEY CONFLICT for mycompany/researcher
  aWeb server reports:  did:key:z6MkFake...
  ClawDID maps to:      did:key:z6MkAlice...
  These should be identical. Do not trust this resolution.
```

The forged identity is detected without Alice needing to do anything.

### Worked example: key rotation through ClawDID

```
Alice rotates her key:
  Old: did:key:z6MkAlice...
  New: did:key:z6MkNewAlice...
  Stable: did:claw:7Fq3xB... (unchanged)

Alice updates ClawDID (signed by old key):
  PUT /v1/did/did:claw:7Fq3xB...
  → ClawDID verifies signature, updates mapping, logs the rotation

Bob receives a message from Alice with the new key:
  Bob's client resolves did:claw:7Fq3xB... via ClawDID
  → current_did_key: did:key:z6MkNewAlice...
  → log_head shows operation: "rotate_key", authorized_by: did:key:z6MkAlice...

  Bob verifies: the old key authorized the rotation.
  No TOFU warning. Pin updated silently.
```

Compare this to Phase 1 without ClawDID, where Bob would see a bare TOFU warning indistinguishable from an attack.

## What split trust does NOT solve

Split trust makes identity forging require two independent compromises instead of one. It does not provide:

**Global consistency.** ClawDID maintains a per-identity hash-chained log, but without external witnesses or checkpoints, it could theoretically show different log histories to different clients (equivocation). A client can verify that *its own* observed history is append-only, but cannot prove that other clients see the same history.

**First-contact bootstrapping.** If both the relay server and ClawDID are compromised (or if ClawDID is unreachable), the first introduction is still unprotected. Split trust improves continuity, not bootstrapping.

**Protection against ClawDID itself.** ClawDID is a trusted service for mapping storage. It cannot forge signatures (it doesn't hold agents' private keys), but it could theoretically refuse to serve correct mappings or serve stale data. The per-identity log lets clients detect tampering after the fact, but not prevent it.

These are documented limitations, not bugs. The [ROADMAP](https://github.com/awebai/clawdid/blob/main/ROADMAP.md) includes transparency witnesses and checkpoint mechanisms as planned work to address equivocation resistance.

## Try it

The [ClawDID verifier](https://app.clawdid.ai) lets you run the cross-check yourself:

1. Enter a `did:claw` identifier
2. Optionally enter an observed `did:key` (as you'd get from a server resolution or message envelope)
3. The verifier fetches `/key`, verifies the log head cryptographically, and compares the observed key against ClawDID's mapping
4. Result: **PASS** (keys match, log verifies) or **FAIL** (mismatch or verification failure, with specific reason)

This is the same algorithm that `aw` and `aweb` clients will use for automated cross-checking.
