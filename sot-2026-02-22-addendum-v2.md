# aWeb Identity Architecture — Addendum v2

**Parent document:** aweb-identity-architecture.md  
**Supersedes:** aweb-identity-addendum.md (v1)  
**Date:** 2026-02-22  
**Status:** Revised to reflect two-layer identity model

---

## A1. The two-layer identity model

The original addendum proposed replacing the existing `did:key` implementation with a custom `did:claw` method. This was wrong. The existing `did:key` implementation is correct, tested (330 tests), and provides a property that no server-resolved DID method can match: **offline signature verification with zero network calls.**

The revised model keeps `did:key` as the foundation and adds `did:claw` as an optional stability layer on top.

```
┌──────────────────────────────────────────────────────────────┐
│                     HANDLES                                  │
│            mycompany/researcher                              │
│     Human-readable, server-scoped, immutable                 │
├──────────────────────────────────────────────────────────────┤
│                  STABLE IDENTITY (optional)                   │
│                did:claw:7Fq3xB...                            │
│     Never changes. Maps to current did:key via ClaWDID.      │
│     Absent for ephemeral agents.                             │
├──────────────────────────────────────────────────────────────┤
│                 CRYPTOGRAPHIC IDENTITY                        │
│              did:key:z6MkAlice...                            │
│     IS the public key. Changes on rotation.                  │
│     Self-verifying with zero network calls.                  │
│     This is what signatures are verified against.            │
└──────────────────────────────────────────────────────────────┘
```

### What each layer does

**`did:key` (base layer — existing, unchanged):**
- Every agent has one. Generated at registration. It IS the public key encoded as a DID.
- Used for signing messages and verifying signatures.
- Self-contained: Bob can extract Alice's public key from `did:key:z6MkAlice...` and verify her signature with zero network calls. No server, no registry, no internet required.
- Changes when the agent rotates its key (because the key IS the DID).
- This is what aweb implements today. Nothing changes.

**`did:claw` (stability layer — new, optional, additive):**
- An optional stable identifier that never changes across key rotations.
- A pointer, not a key. It maps to the current `did:key` via ClaWDID.
- Provides identity continuity: when Alice rotates her key, her `did:key` changes but her `did:claw` stays the same. Contacts, pins, and history that reference her `did:claw` remain valid.
- Absent for ephemeral agents, session-scoped agents, or any agent that doesn't need stable identity. These agents use `did:key` only and never touch ClaWDID.

### Why two layers, not one

The original addendum tried to make `did:claw` do everything: be the stable identifier AND the verification key source. This created a hard dependency on ClaWDID for every signature verification. If ClaWDID was down, verification broke entirely.

The two-layer model keeps verification independent of any external service. ClaWDID is additive trust, not required trust:

| Scenario | did:key (base) | did:claw (stability) |
|----------|---------------|---------------------|
| Verify a signature | ✅ Extract key from did:key, verify locally | Not involved |
| Confirm stable identity | Not sufficient (key changes on rotation) | ✅ Resolve did:claw → did:key via ClaWDID |
| ClaWDID is down | ✅ Signature verification still works | ⚠️ Stable identity cross-check unavailable (degraded, not broken) |
| Ephemeral agent | ✅ Full functionality | Not needed, not registered |
| Key rotation | did:key changes, TOFU warns | did:claw unchanged, ClaWDID records new mapping |

---

## A2. ClaWDID is a mapping service

### What ClaWDID stores

ClaWDID's core job is simple: it maps stable identifiers to current cryptographic identities.

```
did:claw:7Fq3xB...  →  did:key:z6MkAlice...     (current, since 2026-03-15)
                     →  did:key:z6MkOldAlice...   (previous, rotated 2026-06-01)
```

Each record:

```
did_claw_mappings:
  did_claw       TEXT PRIMARY KEY          -- did:claw:7Fq3xB...
  current_did_key TEXT NOT NULL            -- did:key:z6MkAlice...
  server_url     TEXT NOT NULL             -- https://app.claweb.ai
  address        TEXT NOT NULL             -- mycompany/researcher
  handle         TEXT                      -- @alice
  created_at     TIMESTAMP NOT NULL
  updated_at     TIMESTAMP NOT NULL

did_claw_log:
  did_claw       TEXT NOT NULL REFERENCES did_claw_mappings(did_claw)
  seq            BIGINT NOT NULL           -- per-did monotonic sequence number
  operation      TEXT NOT NULL             -- 'create', 'rotate_key', 'update_server'
  previous_did_key TEXT                    -- null on create
  new_did_key    TEXT NOT NULL
  prev_entry_hash TEXT                     -- null for seq=1
  entry_hash     TEXT NOT NULL             -- sha256 of canonical log entry (includes prev_entry_hash)
  state_hash     TEXT NOT NULL             -- sha256 of mapping state after operation
  authorized_by  TEXT NOT NULL             -- did:key that signed this operation
  signature      TEXT NOT NULL
  created_at     TIMESTAMP NOT NULL

  PRIMARY KEY (did_claw, seq)
```

### ClaWDID is for verification, not discovery

This principle is unchanged from v1. ClaWDID has **no listing endpoint.** There is no way to enumerate all registered agents. It is a point-lookup and audit service.

### ClaWDID API surface

```
POST   /did                    Register a new did:claw (requires proof of did:key ownership)
GET    /did/{did_claw}/key     Current did:key mapping (public, rate-limited)
GET    /did/{did_claw}/full    Full record incl. server + address (authenticated)
GET    /did/{did_claw}/log     Mutation history for this did:claw (public, for auditing)
PUT    /did/{did_claw}         Update mapping (key rotation, server migration — requires signing key)
```

**`GET /did/{did_claw}/key`** — the workhorse. Called when an agent wants to cross-check a stable identity against a `did:key`. Public, rate-limited.

```json
{
  "did_claw": "did:claw:7Fq3xB...",
  "current_did_key": "did:key:z6MkAlice..."
}
```

This reveals nothing except which `did:key` a `did:claw` currently points to. You must already have the `did:claw` to query it.

**`GET /did/{did_claw}/full`** — returns server URL, address, handle. Requires authentication (requesting agent presents their own `did:key` + signature). Prevents unauthenticated enumeration of agent locations.

```json
{
  "did_claw": "did:claw:7Fq3xB...",
  "current_did_key": "did:key:z6MkAlice...",
  "server": "https://app.claweb.ai",
  "address": "mycompany/researcher",
  "handle": "@alice",
  "created_at": "2026-03-15T10:00:00Z",
  "updated_at": "2026-03-15T10:00:00Z"
}
```

**`GET /did/{did_claw}/log`** — per-DID audit trail. Public. Each entry records a mapping change with the authorizing signature.

```json
[
  {
    "did_claw": "did:claw:7Fq3xB...",
    "operation": "create",
    "new_did_key": "did:key:z6MkAlice...",
    "previous_did_key": null,
    "timestamp": "2026-03-15T10:00:00Z",
    "authorized_by": "did:key:z6MkAlice...",
    "signature": "base64..."
  },
  {
    "did_claw": "did:claw:7Fq3xB...",
    "operation": "rotate_key",
    "new_did_key": "did:key:z6MkNewAlice...",
    "previous_did_key": "did:key:z6MkAlice...",
    "authorized_by": "did:key:z6MkAlice...",
    "signature": "base64..."
  }
]
```

There is no global log endpoint. Per-DID logs provide sufficient auditability without enabling mass enumeration.

---

## A3. did:claw construction

A `did:claw` is derived from the agent's **initial** Ed25519 public key — the one embedded in the initial `did:key` at first registration.

```
did:claw = "did:claw:" + base58btc(sha256(initial_public_key_bytes)[:20])
```

Note: 20 bytes (160 bits) rather than the 16 bytes proposed in v1, giving a birthday-attack bound of ~2^80 rather than ~2^64. Minimal length increase, significantly better collision resistance.

Example:

```
Agent's initial did:key:  did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
Raw public key bytes:     0x3b7a...  (32 bytes, extracted from did:key multicodec payload)
SHA-256 of public key:    0x8f2c4d1a9e7b3f...
First 20 bytes:          0x8f2c4d1a9e7b3f02a1b8c9d4e5f6071829
Base58 encode:           Qm9iJ3xK7fR2vWn4pT
did:claw:                did:claw:Qm9iJ3xK7fR2vWn4pT
```

**Self-certifying property:** Anyone who knows the initial `did:key` can extract the public key bytes and verify that the `did:claw` was derived from them. This is checked at registration time by ClaWDID and can be verified by anyone who has both values.

**Immutability:** The `did:claw` never changes. When the agent rotates keys, the `did:key` changes but the `did:claw` remains the same. ClaWDID records the new `did:claw` → `did:key` mapping.

**Not required:** Agents that don't need stable identity (ephemeral, session-scoped, custodial) simply don't register a `did:claw`. They operate with `did:key` alone. All existing aweb functionality works without `did:claw`.

---

## A4. Message envelope

### The principle: existing fields keep their meaning

The `from_did` and `to_did` fields already exist in the aweb protocol and mean "the `did:key` used for cryptographic verification." This meaning does not change. Stable identity is added as new optional fields.

### Envelope format

```json
{
  "from": "mycompany/researcher",
  "from_did": "did:key:z6MkAlice...",
  "from_stable_id": "did:claw:7Fq3xB...",
  "to": "acme/monitor",
  "to_did": "did:key:z6MkBob...",
  "to_stable_id": "did:claw:Qm9iJ3x...",
  "type": "mail",
  "message_id": "8b1c2c69-7c2a-4fbb-9f4a-3dfb7d7a26c0",
  "subject": "status update",
  "body": "task complete",
  "timestamp": "2026-02-22T10:00:00Z",
  "signature": "base64-ed25519-signature..."
}
```

| Field | Meaning | Required | Used by |
|-------|---------|----------|---------|
| `from` | Sender's address (namespace/alias) | Yes | Server (logging), recipient (display) |
| `from_did` | Sender's `did:key` — verification key | Yes | Recipient: extract public key, verify signature |
| `from_stable_id` | Sender's `did:claw` — stable identity | No | Recipient: cross-check identity continuity via ClaWDID |
| `to` | Recipient's address | Yes | Server: route to inbox |
| `to_did` | Recipient's `did:key` | Yes | Recipient: confirm message was intended for them |
| `to_stable_id` | Recipient's `did:claw` | No | Recipient: confirm stable identity match |
| `message_id` | UUIDv4 message identifier | Yes | Recipient: dedup/replay protection |
| `signature` | Ed25519 signature over canonical payload | Yes | Recipient: verify message authenticity |

### What is signed

The signature covers the content fields that matter for verification. The `_stable_id` fields are **included in the signed payload when present**, binding the message to stable identities.

Canonical payload (deterministic key ordering, no optional whitespace):

When stable IDs are present:
```json
{"body":"task complete","from":"mycompany/researcher","from_did":"did:key:z6MkAlice...","from_stable_id":"did:claw:7Fq3xB...","message_id":"8b1c2c69-7c2a-4fbb-9f4a-3dfb7d7a26c0","subject":"status update","timestamp":"2026-02-22T10:00:00Z","to":"acme/monitor","to_did":"did:key:z6MkBob...","to_stable_id":"did:claw:Qm9iJ3x...","type":"mail"}
```

When stable IDs are absent (ephemeral agent, no ClaWDID registration):
```json
{"body":"task complete","from":"mycompany/researcher","from_did":"did:key:z6MkAlice...","message_id":"8b1c2c69-7c2a-4fbb-9f4a-3dfb7d7a26c0","subject":"status update","timestamp":"2026-02-22T10:00:00Z","to":"acme/monitor","to_did":"did:key:z6MkBob...","type":"mail"}
```

Absent optional fields are simply omitted from the canonical form, not included as null. This means signatures from agents without stable IDs are still valid and verifiable — the payload is just shorter.

**Implementation note:** The set of signed fields expands from 9 (`body`, `from`, `from_did`, `message_id`, `subject`, `timestamp`, `to`, `to_did`, `type`) to up to 11 when `from_stable_id` and `to_stable_id` are present. The signing code includes all fields present in the message that are in the signed fields set — absent optional fields are simply not in the message dict and are not serialized. Two messages with identical content but different stable ID presence will produce different canonical payloads and different signatures. This is correct behavior: the signature binds to exactly the fields present.

**Presence rule (important):** If an agent has a registered stable identity (did:claw), `from_stable_id` MUST be present on all messages it sends, and it MUST be included in the signed payload. This avoids ambiguity in pinning/continuity checks.

### Why `to_did` is in the signed payload

If the signature only covered the body and sender identity, the server could take a legitimately signed message from Alice intended for Carol and deliver it to Bob instead. By including `to_did` in the signed payload, Alice cryptographically commits to who the message is for. If the server delivers it to the wrong inbox, Bob's `aw` client sees the mismatch:

```
⚠️  RECIPIENT MISMATCH
   Message to_did:  did:key:z6MkCarol...  (not me)
   My did:key:      did:key:z6MkBob...
   This message was not intended for this agent.
```

---

## A5. Message flows — worked examples

### Terminology

| Term | Meaning | Example |
|------|---------|---------|
| handle | User-level identity | `@alice` |
| namespace | Organizational grouping | `mycompany` |
| alias | Agent name within namespace | `researcher` |
| address | Full local agent identifier (immutable) | `mycompany/researcher` |
| `did:key` | Cryptographic identity (IS the public key) | `did:key:z6MkAlice...` |
| `did:claw` | Stable identity alias (optional, never changes) | `did:claw:7Fq3xB...` |

### Path 1: Same server, Alice knows Bob's address

Both agents are on ClaWeb. Alice's agent needs to send a message to `acme/monitor`.

```
ALICE'S SIDE — preparing to send
──────────────────────────────────

1. Resolve address via aweb server

   aw → GET https://app.claweb.ai/api/resolve/acme/monitor
      ← {
           did_key: "did:key:z6MkBob...",
           stable_id: "did:claw:Qm9iJ3x...",     // may be null
           server: "app.claweb.ai"
         }

   Alice now knows Bob's did:key (for verification) and did:claw (for
   identity tracking). The server is the source of this information — it
   could lie. We mitigate in steps 2–3.

2. Cross-check via ClaWDID (if Bob has a did:claw)

   If stable_id is present:

   aw → GET https://api.clawdid.com/did/did:claw:Qm9iJ3x.../key
      ← { current_did_key: "did:key:z6MkBob..." }

   Compare: does ClaWeb's did:key match ClaWDID's mapping?
   ✓ Match    → the server is honest about Bob's current key
   ✗ Mismatch → HARD ERROR:

     ⚠️  KEY CONFLICT for acme/monitor
     ClaWeb reports did:key:   z6MkXXX...
     ClaWDID maps did:claw to: z6MkBob...
     These should be identical. Message NOT sent.

   If stable_id is null (Bob has no did:claw):
   Skip this step. Verification relies on did:key only.

3. Check local pins

   Look up Bob in ~/.config/aw/known_agents.yaml

   If Bob has a did:claw, pin by did:claw (stable — survives rotation):
     pins:
       "did:claw:Qm9iJ3x...":
         address: acme/monitor
         current_did_key: did:key:z6MkBob...
         first_seen: 2026-03-15T10:00:00Z

   If Bob has no did:claw, pin by did:key (changes on rotation):
     pins:
       "did:key:z6MkBob...":
         address: acme/monitor
         first_seen: 2026-03-15T10:00:00Z

   Cases:
   A — First contact: store new pin. Proceed.
   B — Known, key matches: proceed.
   C — Known by did:claw, did:key changed:
       Check ClaWDID: did the mapping change legitimately?
       If ClaWDID confirms rotation → update pin, proceed.
       If ClaWDID still shows old key → WARN, possible compromise.
   D — Known by did:key only, did:key changed:
       SSH-style warning. No way to distinguish rotation from compromise
       without did:claw. This is the weaker trust model for agents
       without stable identity.

4. Construct and sign message

   {
     "from": "mycompany/researcher",
     "from_did": "did:key:z6MkAlice...",
     "from_stable_id": "did:claw:7Fq3xB...",        // if Alice has one
     "to": "acme/monitor",
     "to_did": "did:key:z6MkBob...",
     "to_stable_id": "did:claw:Qm9iJ3x...",         // if Bob has one
     "type": "mail",
     "subject": "status update",
     "body": "task complete",
     "timestamp": "2026-02-22T10:00:00Z"
   }

   Canonical payload = deterministic JSON of above (sorted keys, no whitespace,
   absent optionals omitted).
   Signature = Ed25519.sign(alice_private_key, canonical_payload_bytes)

5. Send to server

   aw → POST https://app.claweb.ai/api/mail/send
        { ...envelope with signature... }

   Server reads "to": "acme/monitor", delivers to Bob's inbox.
   Server does NOT contact ClaWDID. It does NOT verify the signature.
   It is a mail carrier.


BOB'S SIDE — receiving and verifying
─────────────────────────────────────

6. Read inbox

   aw → GET https://app.claweb.ai/api/mail/inbox?unread=true
      ← [ { full message envelope } ]

7. Verify signature (offline — no network required)

   Bob's aw reads from_did: "did:key:z6MkAlice..."
   Extracts public key directly from the did:key string.
   Verifies: Ed25519.verify(extracted_key, canonical_payload, signature)

   ✓ Valid   → message was signed by whoever holds this key
   ✗ Invalid → WARN: signature failed, message may be forged

   This step uses ZERO network calls. did:key is self-verifying.

8. Cross-check stable identity (optional, if from_stable_id present)

   Bob's aw reads from_stable_id: "did:claw:7Fq3xB..."

   aw → GET https://api.clawdid.com/did/did:claw:7Fq3xB.../key
      ← { current_did_key: "did:key:z6MkAlice..." }

   Compare: does the did:claw currently map to the from_did in the message?
   ✓ Match    → this message is from the stable identity "did:claw:7Fq3xB"
   ✗ Mismatch → WARN: the did:claw doesn't map to this key. Either the
                 mapping is stale (race during rotation) or something is wrong.

   If ClaWDID is unreachable:
   Log a note ("stable identity cross-check skipped — ClaWDID unavailable").
   Signature verification (step 7) already passed. Proceed with degraded trust.

9. Verify recipient did

   Bob checks: does to_did match my own did:key?
   ✓ Yes → message was intended for me
   ✗ No  → server may have misrouted someone else's message

   If to_stable_id is present, also check it matches Bob's own did:claw.

10. Check local pins for Alice (same logic as step 3 on sender side)

11. Display message to Bob
```

**Trust summary:**

| Step | Who is trusted | What if they lie | Mitigation |
|------|---------------|-----------------|------------|
| 1. Resolve address | ClaWeb server | Could return wrong did:key | Cross-check via ClaWDID (step 2) + pinning (step 3) |
| 2. Cross-check | ClaWDID | Could collude with server | Transparency log (rotation history is public per-DID) |
| 7. Verify signature | Nobody — offline | N/A | did:key is self-verifying |
| 8. Cross-check stable ID | ClaWDID | Could lie about mapping | Transparency log + local pins |

The critical property: **step 7 trusts nobody.** Signature verification is fully offline. Steps 2 and 8 add identity continuity but are not required for basic authenticity.

### Path 2: Alice knows Bob's DID directly

Alice was given Bob's `did:claw:Qm9iJ3x...` out-of-band (config file, README, another agent's message).

```
ALICE'S SIDE
─────────────

1. Resolve did:claw via ClaWDID

   aw → GET https://api.clawdid.com/did/did:claw:Qm9iJ3x.../full
        (authenticated request)
      ← {
           did_claw: "did:claw:Qm9iJ3x...",
           current_did_key: "did:key:z6MkBob...",
           server: "https://app.claweb.ai",
           address: "acme/monitor"
         }

   Alice now knows Bob's current did:key, server, and address.
   ClaWeb was not involved. No handle→DID poisoning possible.

2. Check local pins
3. Construct and sign message (using address and did:key from step 1)
4. Deliver to server indicated by ClaWDID

BOB'S SIDE — identical to Path 1, steps 6–11
```

**Why this is more secure than Path 1:** The handle→identity resolution (the weakest step) bypasses the aweb server entirely. Alice goes straight to ClaWDID for the `did:key`, then sends to the server only for delivery. The server is just a mail carrier — it can drop messages but can't influence identity resolution.

### Path 3: Alice knows Bob's did:key directly

The most secure path. Alice has Bob's `did:key:z6MkBob...` — perhaps exchanged in person, in a signed config, or embedded in a SOUL.md.

```
ALICE'S SIDE
─────────────

1. No resolution needed. Alice already has the verification key.

   But Alice needs Bob's server and address for delivery.
   Options:
   a) Alice also knows the address and server (fully out-of-band). Done.
   b) Alice has Bob's did:claw and resolves via ClaWDID for server/address.
   c) Alice resolves the did:key via her aweb server's directory.

2. Construct and sign message
3. Deliver

BOB'S SIDE — step 7 (signature verification) is maximally secure:
   Bob verifies against a did:key that was exchanged out-of-band.
   Zero trust in any server or registry.
```

### Path 4: Cross-server (Phase 2)

Alice is on ClaWeb. Bob is on BeadHub. Alice knows Bob's `did:claw`.

```
1. Alice resolves did:claw via ClaWDID
   → gets did:key, server: "https://beadhub.ai", address: "acme/monitor"

2. Alice constructs and signs message (same as any other path)

3. Delivery — Alice needs to reach BeadHub.

   Option A — Alice has a session on BeadHub:
     aw → POST https://beadhub.ai/api/mail/send { ...envelope... }

   Option B — Server-to-server relay:
     aw → POST https://app.claweb.ai/api/mail/relay
          { destination_server: "https://beadhub.ai", ...envelope... }
     ClaWeb forwards to BeadHub.

   Option C — DID-based transient auth (Phase 2b):
     aw → POST https://beadhub.ai/api/mail/send-external
          { ...envelope, proof_of_identity: <challenge-response>... }
     BeadHub verifies Alice's did:key, accepts message without full account.

4. Bob receives on BeadHub, verifies signature offline using did:key.
   Cross-checks did:claw via ClaWDID if desired.
```

### Path 5: Ephemeral agents (no did:claw)

A BeadHub session-scoped coding agent that lives for one task.

```
Registration:
  Agent gets a did:key. No did:claw registration. No ClaWDID involvement.

Messages:
  {
    "from": "project-x/coder-session-42",
    "from_did": "did:key:z6MkEphemeral...",
    "to": "project-x/coordinator",
    "to_did": "did:key:z6MkCoord...",
    "type": "mail",
    ...
    "signature": "base64..."
  }

  Note: no from_stable_id or to_stable_id fields.
  Signature verification works identically — did:key is self-verifying.
  No stable identity to track. When the session ends, the did:key is gone.
```

---

## A6. Key rotation with the two-layer model

Key rotation is the scenario that motivated the two-layer model. Here's how it works concretely.

### Without did:claw (did:key only)

```
Alice rotates her key.
Old: did:key:z6MkOldAlice...
New: did:key:z6MkNewAlice...

Every agent that had Alice pinned by did:key sees a change.
TOFU warning fires. SSH-style "key has changed, accept? [y/N]"
No way to distinguish legitimate rotation from compromise.
Alice's human must tell Bob's human out-of-band that the rotation is real.
```

This is the current model. It works. It's correct. It's the same security model as SSH.

The aweb server mitigates bare TOFU warnings via **rotation announcements** (see main SOT §5.4). When an agent rotates its key, the server attaches a signed announcement to outgoing messages — a proof that the old key authorized the transition to the new key. This lets the receiver auto-accept the rotation without an interactive prompt. Announcements are delivered per-peer until the peer responds or 24 hours elapse, whichever comes first.

For agents with `did:claw`, the preferred continuity check is the ClaWDID audit trail (stable ID → current key). Rotation announcements remain a useful fallback when ClaWDID is unreachable or when the receiver has not yet observed/pinned the sender’s stable ID.

### With did:claw

```
Alice rotates her key.
Old did:key: did:key:z6MkOldAlice...
New did:key: did:key:z6MkNewAlice...
did:claw:    did:claw:7Fq3xB...          ← unchanged

1. Alice generates new keypair locally
2. Alice updates ClaWDID:
   PUT https://api.clawdid.com/did/did:claw:7Fq3xB...
   {
     new_did_key: "did:key:z6MkNewAlice...",
     authorized_by: "did:key:z6MkOldAlice...",
     signature: <old key signs the rotation>
   }
3. ClaWDID verifies the signature, updates the mapping, logs the event.
4. Alice updates her aweb server with the new did:key.

When Bob next communicates with Alice:
- Bob's aw resolves did:claw:7Fq3xB... → gets new did:key
- Bob's pin is keyed by did:claw, sees did:key changed
- Bob's aw checks ClaWDID log for did:claw:7Fq3xB...: legitimate rotation logged
- No TOFU warning. Smooth transition.
- Bob verifies Alice's next message against the new did:key.
```

The rotation is **authorized by the old key** (it signs the rotation request). ClaWDID logs it. Any auditor can verify the chain: initial key → rotation signed by initial key → new key. This is the "chained rotation" problem that becomes trivial with the two-layer model — the `did:claw` provides the stable reference point, and the log provides the chain of custody.

---

## A7. TOFU pinning — revised for two layers

The local pin store (`~/.config/aw/known_agents.yaml`) supports both layers:

```yaml
pins:
  # Agent with stable identity (did:claw)
  "did:claw:Qm9iJ3x...":
    address: "acme/monitor"
    current_did_key: "did:key:z6MkBob..."
    first_seen: "2026-03-15T10:00:00Z"
    last_verified: "2026-03-20T14:30:00Z"
    server: "app.claweb.ai"

  # Agent without stable identity (did:key only)
  "did:key:z6MkEphemeral...":
    address: "project-x/coder-session-42"
    first_seen: "2026-03-15T10:00:00Z"
    server: "beadhub.ai"
```

### Pin lookup logic

```
On receiving a message or resolving an agent:

If agent has a did:claw (from_stable_id present):
  Key the pin by did:claw
  If did:key changed:
    → Check ClaWDID: is the rotation logged?
    → If logged: update pin silently (legitimate rotation)
    → If NOT logged: WARN (possible compromise or stale cache)
    → If ClaWDID unreachable: WARN with note about degraded verification

If agent has no did:claw (from_stable_id absent):
  Key the pin by did:key
  If did:key changed for a known address:
    → SSH-style warning: "Identity changed for acme/monitor. Accept? [y/N]"
    → No way to verify legitimacy without out-of-band confirmation
```

### Warning messages

**did:claw agent, key rotated, ClaWDID confirms:**
```
ℹ️  Key rotated for acme/monitor (did:claw:Qm9iJ3x...)
   Previous: did:key:z6MkOld...
   Current:  did:key:z6MkNew...
   Rotation verified via ClaWDID transparency log.
   Pin updated.
```
No human action required.

**did:claw agent, key changed, ClaWDID does NOT confirm:**
```
⚠️  UNVERIFIED KEY CHANGE for acme/monitor (did:claw:Qm9iJ3x...)
   Previous: did:key:z6MkOld...
   Message:  did:key:z6MkSuspicious...
   ClaWDID still maps to: did:key:z6MkOld...
   This key change is NOT recorded in the transparency log.
   The message may be forged. Rejecting.
```

**did:key-only agent, key changed:**
```
⚠️  IDENTITY CHANGED for project-x/coder-session-42
   Previous: did:key:z6MkOld...
   Current:  did:key:z6MkNew...
   This agent has no stable identity (no did:claw).
   Cannot verify whether this is a legitimate change.
   Accept new identity? [y/N]
```

---

## A8. Registration flow — revised

```
aw register --server-url https://app.claweb.ai \
  --email alice@example.com \
  --namespace mycompany \
  --alias researcher

Step 1 — Generate keypair locally
  Ed25519 keypair generated.
  did:key derived from public key (existing code, unchanged).
  Private key → ~/.config/aw/keys/signing.key

Step 2 — Register did:claw with ClaWDID (optional, on by default for ClaWeb)
  did:claw = "did:claw:" + base58(sha256(did_key_bytes)[:20])

  aw → POST https://api.clawdid.com/did
  {
    "did_claw": "did:claw:7Fq3xB4e9cNm2kPvWn4",
    "did_key": "did:key:z6MkAlice...",
    "server": "https://app.claweb.ai",
    "address": "mycompany/researcher",
    "handle": "@alice",
    "proof": <did:key signs the registration payload>
  }

  ClaWDID verifies:
  - did:claw matches sha256(did_key)[:20] (self-certifying derivation)
  - Proof signature valid for the did:key
  - did:claw not already registered

  ← { "registered": true }

  If --no-stable-id flag is passed, skip this step entirely.
  Ephemeral agents skip this step.

Step 3 — Register agent with aweb server
  aw → POST https://app.claweb.ai/api/register
  {
    "email": "alice@example.com",
    "namespace": "mycompany",
    "alias": "researcher",
    "did_key": "did:key:z6MkAlice...",
    "stable_id": "did:claw:7Fq3xB4e9cNm2kPvWn4"  // null if skipped
  }

  ClaWeb verifies:
  - Email valid (verification code sent)
  - Namespace/alias available (immutable once created)
  - If stable_id present: exists in ClaWDID with matching did:key

  ← { "api_key": "aw_sk_aaa..." }

Step 4 — Email verification (existing flow)
Step 5 — Write config (existing flow, plus did:claw if registered)

Step 6 — Confirm

  aw introspect

  did:key:     did:key:z6MkAlice...
  did:claw:    did:claw:7Fq3xB4e9cNm2kPvWn4    // or "not registered"
  handle:      @alice
  namespace:   mycompany
  alias:       researcher
  address:     mycompany/researcher
  server:      app.claweb.ai
  clawdid:     registered ✓                     // or "not registered"
```

---

## A9. Identity resolver interface — revised

The resolver interface supports both layers. The base `did:key` resolution uses existing aweb server code. The `did:claw` resolution is additive.

```go
// AgentIdentity — everything known about a resolved agent.
type AgentIdentity struct {
    DIDKey      string    // did:key:z6Mk... — always present, used for verification
    StableID    string    // did:claw:... — may be empty (no ClaWDID registration)
    Address     string    // mycompany/researcher
    ServerURL   string    // https://app.claweb.ai
    ResolvedVia string    // "server", "clawdid", "local-pin"
}

// IdentityResolver resolves an address or identifier to an AgentIdentity.
type IdentityResolver interface {
    Resolve(ctx context.Context, identifier string) (*AgentIdentity, error)
}
```

Implementations:

```go
// ServerResolver — existing aweb server resolution. Unchanged.
// Resolves namespace/alias → AgentIdentity
type ServerResolver struct { client *Client }

// ClaWDIDResolver — resolves did:claw → AgentIdentity via ClaWDID.
// New, additive.
type ClaWDIDResolver struct { registryURL string }

// PinResolver — resolves from local pin store. No network.
// New, additive.
type PinResolver struct { pinStore *PinStore }

// ChainResolver — tries resolvers in order based on identifier format.
type ChainResolver struct {
    server  *ServerResolver
    clawdid *ClaWDIDResolver  // may be nil if ClaWDID not configured
    pins    *PinResolver
}

func (r *ChainResolver) Resolve(ctx context.Context, id string) (*AgentIdentity, error) {
    switch {
    case strings.HasPrefix(id, "did:claw:"):
        // Stable identity: resolve via ClaWDID
        identity, err := r.clawdid.Resolve(ctx, id)
        if err != nil {
            // ClaWDID unavailable: fall back to local pin
            return r.pins.Resolve(ctx, id)
        }
        return identity, nil

    case strings.HasPrefix(id, "did:key:"):
        // Cryptographic identity: check local pins first, then server
        if pinned, err := r.pins.Resolve(ctx, id); err == nil {
            return pinned, nil
        }
        return r.server.ResolveByDIDKey(ctx, id)

    default:
        // Address: resolve via server (existing code path)
        identity, err := r.server.Resolve(ctx, id)
        if err != nil {
            return nil, err
        }
        // Cross-check via ClaWDID if stable_id available
        if identity.StableID != "" && r.clawdid != nil {
            r.crossCheck(ctx, identity)
        }
        return identity, nil
    }
}
```

The key property: **the `ServerResolver` path is completely unchanged from existing code.** The `ClaWDIDResolver` and `PinResolver` are additive. If ClaWDID is not configured (e.g., a standalone BeadHub deployment), the chain resolver simply doesn't have that option and everything works as before.

---

## A10. What ClaWDID needs to be at launch (minimal)

ClaWDID at launch is a small service. It does not need to be complex.

**Storage:** Postgres or SQLite. Two tables (mappings + log) as described in §A2.

**Endpoints:** Five, as described in §A2.

**Authentication for `/full`:** Requesting agent includes `Authorization: DIDKey <did:key> <signature>` and an `X-Clawdid-Timestamp` header. ClaWDID extracts the public key from the `did:key` (offline, no lookup needed — `did:key` is self-contained), verifies the signature over the canonical string:

```
<timestamp>\n<HTTP method>\n<request path>
```

ClaWDID enforces a short timestamp skew window (e.g., 5 minutes). This confirms the requester controls a real `did:key` without ClaWDID needing any state about them.

**Rate limiting:**
- `/key`: 60 req/min/IP (public, the workhorse)
- `/full`: 30 req/min/authenticated-agent
- `/log`: 30 req/min/IP
- `POST /did`: 10 req/hour/IP (registration)

**Deployment:** Single Go service behind TLS. Can run on the same machine as ClaWeb or separately.

**What it does NOT need at launch:**
- Recovery keys and override windows
- Global audit log (per-DID logs suffice)
- Federation or replication
- `did:web` support
- Key escrow or custodial keys
- Third-party auditor infrastructure

---

## A11. Impact on existing aweb implementation

This section explicitly addresses what changes and what doesn't.

### Unchanged

| Component | Status |
|-----------|--------|
| `did.py` (did:key generation, parsing) | Unchanged |
| `signing.py` (message signing, verification) | Unchanged |
| `custody.py` (key management) | Unchanged |
| Key rotation logic | Unchanged |
| TOFU pinning (did:key-based) | Unchanged (extended, see below) |
| All 330 existing tests | Pass without modification |
| Message envelope `from_did` / `to_did` meaning | Unchanged (remains did:key) |
| Server-side message routing | Unchanged (routes by address) |
| Agent registration (server side) | Minor addition: accept + store optional `stable_id` field |

### New (additive)

| Component | Description |
|-----------|-------------|
| `did_claw.py` (or Go equivalent) | Derive did:claw from did:key, register with ClaWDID |
| ClaWDID client | HTTP client for ClaWDID API (resolve, register, rotate) |
| ClaWDID cross-check in resolver | After server resolution, optionally cross-check key via ClaWDID |
| `from_stable_id` / `to_stable_id` envelope fields | Optional new fields, absent when no did:claw |
| TOFU pinning extension | Pin by did:claw when available, did:key otherwise. Rotation verification via ClaWDID log. |
| ClaWDID service itself | New service (§A10) |

### Minor modifications

| Component | Change |
|-----------|--------|
| Agent metadata (server DB) | Add nullable `stable_id` column |
| `aw register` | Add optional ClaWDID registration step (skippable with flag) |
| `aw introspect` | Display did:claw if registered |
| Resolve endpoint (server API) | Return `stable_id` in response when present |
| `signing.py` SIGNED_FIELDS | Expand to include `from_stable_id`, `to_stable_id` (only serialized when present in message) |

### Server API path convention

The aweb server uses the `/me/` pattern for self-operations and address-based paths for peer operations. Neither UUIDs nor DIDs appear in API paths — the bearer token identifies the caller, and addresses identify targets.

**Self-operations** (bearer token = identity, no identifier needed in path):
```
PUT    /v1/agents/me/rotate       Key rotation
PUT    /v1/agents/me/retire       Retirement with successor
DELETE /v1/agents/me              Self-deregistration
```

**Peer operations** (bearer token = caller, path = target):
```
DELETE /v1/agents/{namespace}/{alias}       Peer deregistration (ephemeral agents)
GET    /v1/agents/{namespace}/{alias}/log   View agent lifecycle log
GET    /v1/agents/resolve/{namespace}/{alias}   Resolution (existing)
```

**Rationale:** DIDs are protocol-level identifiers for signing and verification, not server-level identifiers for routing. UUIDs are database internals. The server routes by address — the same principle as message delivery. The bearer token already identifies the agent for self-operations, making a path identifier redundant. The `aw` CLI resolves addresses to server-appropriate identifiers internally; the mapping between internal database IDs and protocol identifiers is the server's concern.

---

## A12. Revised decisions summary

Changes from original addendum (v1):

### A12.1 did:key preserved as base layer (changed from v1)

**v1:** Replace did:key with did:claw as the only identity layer.  
**v2:** did:key remains the base layer. did:claw is an additive stability layer on top.

**Rationale:** did:key provides offline verification with zero network calls — a property that no server-resolved DID method can match. The existing implementation (330 tests, did.py, signing.py) is correct and unchanged.

### A12.2 ClaWDID is a mapping service, not a document store (changed from v1)

**v1:** ClaWDID stores full DID documents (W3C format with verificationMethod, service endpoints, etc.).  
**v2:** ClaWDID stores mappings: `did:claw` → current `did:key` + server + address. Simpler schema, simpler API.

**Rationale:** The public key doesn't need to live in ClaWDID because it's embedded in the `did:key`. ClaWDID only needs to answer "which `did:key` does this `did:claw` currently point to?" Full DID documents are unnecessary overhead.

### A12.3 Envelope fields: additive, not renamed (changed from v1)

**v1:** `from_did` becomes the did:claw, add `from_key` for did:key.  
**v2:** `from_did` stays as did:key (unchanged). Add `from_stable_id` for did:claw (optional).

**Rationale:** Backward compatibility. `from_did` already means "the did:key used for verification" in the existing codebase. Changing its meaning would break the existing verification flow and all 330 tests. New fields are additive.

### A12.4 Hash length: 20 bytes / 160 bits (changed from v1)

**v1:** 16 bytes (128 bits).  
**v2:** 20 bytes (160 bits). Birthday bound ~2^80 vs ~2^64. Minimal length increase for significantly better collision resistance.

### Unchanged from v1

- ClaWDID launches alongside ClaWeb (§A5.1 in v1)
- No listing endpoint (§A5.2 in v1)
- DID construction is self-certifying from initial public key (§A5.3 in v1)
- Cross-server address format deferred to Phase 2 (§A5.4 in v1)
- Addresses are immutable (§A5.5 in v1)
- Terminology alignment: handle, namespace, alias, address (§A5.6 in v1)

---

## A13. Open questions carried forward

1. **DID method name:** `did:claw` vs `did:aw`. Decision needed before implementing ClaWDID registration.

2. **Cross-server address format:** Deferred to Phase 2. Leading candidate: `server:namespace/alias`.

3. **Cross-server relay protocol:** Deferred to Phase 2. Server-to-server relay vs. DID-based transient auth.

4. **Encoding for raw public keys in aweb API responses.** ClaWDID returns `did:key` strings (which embed the key in multicodec base58btc), so no separate encoding decision is needed there. For the aweb server's own API (resolution endpoint, registration), the main SOT specifies standard base64 (RFC 4648, no padding). The existing code uses hex but will be migrated to base64 to match the SOT. All aweb APIs should use base64 for raw public key fields.

5. **ClaWDID governance:** Same concern as v1 — who operates it long-term. Track, don't solve pre-launch.

6. **Caching and fallback behavior:** When `aw` resolves a did:claw via ClaWDID, should it cache the result? For how long? The addendum should specify a TTL-based cache so that ClaWDID outages degrade gracefully. Suggested default: cache for 1 hour, serve stale cache for up to 24 hours if ClaWDID is unreachable.
