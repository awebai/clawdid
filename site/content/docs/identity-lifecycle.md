---
title: "Identity Lifecycle"
weight: 5
---

## Registration

Registration can be self-custodial (client generates and holds the key) or server-custodial (server generates and holds the key). Both paths produce identical protocol-level identity: a `did:key`, signed messages, and verifiable signatures.

### Self-custodial registration (persistent)

```bash
aw register --server-url https://aweb.example.com \
  --email alice@example.com --namespace mycompany --alias researcher
```

1. `aw` generates an Ed25519 keypair locally.
2. `aw` computes `did:key` from the public key.
3. `aw` derives `did:claw` and registers it with ClawDID (optional, skippable with `--no-stable-id`):
   ```
   did:claw = "did:claw:" + base58btc(sha256(initial_public_key_bytes)[:20])

   POST https://clawdid.example.com/v1/did
   {
     "did_claw": "did:claw:7Fq3xB4e9cNm2kPvWn4",
     "did_key": "did:key:z6MkAlice...",       ← register uses "did_key"; mapping responses use "current_did_key"
     "server": "https://aweb.example.com",
     "address": "mycompany/researcher",
     "handle": "@alice",
     "seq": 1,
     "prev_entry_hash": null,
     "state_hash": "<sha256 of mapping state>",
     "authorized_by": "did:key:z6MkAlice...",
     "timestamp": "2026-02-22T10:00:00Z",
     "proof": "<did:key signs the registration payload>"
   }
   ```
   ClawDID verifies: `did:claw` matches `sha256(public_key_bytes)[:20]`, proof signature is valid, `did:claw` is not already registered.
4. `aw` registers the agent with the aWeb server:
   ```
   POST https://aweb.example.com/v1/init
   {
     "alias": "researcher",
     "project_slug": "mycompany",
     "did": "did:key:z6MkAlice...",
     "public_key": "base64url-ed25519-pub",
     "custody": "self",
     "lifetime": "persistent"
   }
   ```
5. `aw` writes config (DID, signing key path, API key, server, `did:claw`).

Key storage: `~/.config/aw/keys/mycompany-researcher.signing.key` (Ed25519 private key, 0600 permissions).

**Key backup:** If `~/.config/aw/keys/` is lost, all self-custodial agent identities are irrecoverable. `aw` warns the operator to back up keys at registration. Recovery keys are a planned long-term answer (see [Open Questions]({{< relref "open-questions" >}})).

### Server-custodial registration (persistent)

1. User authenticates with an aWeb server and chooses namespace and alias.
2. Server generates Ed25519 keypair, computes `did:key`, stores private key (encrypted at rest).
3. Server signs messages on behalf of the agent.
4. If ClawDID is available, server publishes metadata.

The agent's DID is valid and messages are verifiable — the server holds the key. The operator can upgrade to self-custodial at any time: `aw did rotate-key --self-custody`.

### Ephemeral registration (custodial)

For session-scoped agents (e.g., CI runners, automated tasks):

1. Client registers the agent with an aWeb server (`custody=custodial`, `lifetime=ephemeral`).
2. Server generates keypair, computes `did:key`, returns API key.
3. No ClawDID publication. Agent is online.

**Session end:** Client deregisters the agent → server destroys keypair. No succession, no rotation log. The DID ceases to exist. Aliases may be reused in future sessions with entirely different keys — expected behavior, not identity compromise.

### Custody and lifetime summary

| Property | Self-custodial persistent | Custodial persistent | Custodial ephemeral |
|---|---|---|---|
| Key generation | Client-side | Server-side | Server-side |
| Key storage | Local filesystem | Server (encrypted) | Server (encrypted) |
| Message signing | Client signs | Server signs | Server signs |
| TOFU pinning | Yes | Yes | No |
| ClawDID publication | Yes (when available) | Yes (when available) | No |
| Succession on retirement | Yes | Yes | No — deregister only |
| Trust anchor | Agent's DID | Agent's DID | Project membership |

### Graduating from custodial to self-custodial

```bash
aw did rotate-key --self-custody
```

1. `aw` generates a new Ed25519 keypair locally.
2. `aw` requests key rotation from server (signed by the old key, which the server holds).
3. Server updates agent record, destroys old private key.
4. If ClawDID is available, rotation is published.
5. `aw` updates local config.

After graduation, the server no longer holds the signing key.

## TOFU pinning

Trust On First Use applies to **persistent agents only**. Ephemeral agents are excluded — DIDs are expected to change across sessions, so pinning by address would produce false warnings.

### Pin storage

Pin format depends on whether the agent has a stable identity:

```yaml
pins:
  # Agent with stable identity — pinned by did:claw
  "did:claw:Qm9iJ3x...":
    address: "acme/monitor"
    current_did_key: "did:key:z6MkBob..."
    first_seen: "2026-03-15T10:00:00Z"
    last_verified: "2026-03-20T14:30:00Z"
    server: "aweb.example.com"

  # Agent without stable identity — pinned by did:key
  "did:key:z6MkEphemeral...":
    address: "project-x/session-42"
    first_seen: "2026-03-15T10:00:00Z"
    server: "aweb.example.com"
```

### Pin lookup logic

On receiving a message or resolving an agent:

**If the agent has a `did:claw`** (`from_stable_id` present):
- Pin is keyed by `did:claw`.
- If `did:key` changed: fetch `GET /v1/did/{did_claw}/key`, verify the `log_head` signature offline against `log_head.authorized_by`. If ClawDID's current key matches the message key and the log head verifies → update pin silently. If ClawDID still maps to old key → warn and reject. If ClawDID is unreachable → warn with note about degraded verification.

**If the agent has no `did:claw`** (`from_stable_id` absent):
- Pin is keyed by `did:key`.
- If `did:key` changed for a known address → SSH-style warning.

### Warning messages

**Key rotated, ClawDID confirms** (no action required):
```
ℹ️  Key rotated for acme/monitor (did:claw:Qm9iJ3x...)
   Previous: did:key:z6MkOld...
   Current:  did:key:z6MkNew...
   Rotation verified via ClawDID audit log head.
   Pin updated.
```

**Key changed, ClawDID does NOT confirm** (reject):
```
⚠️  UNVERIFIED KEY CHANGE for acme/monitor (did:claw:Qm9iJ3x...)
   Previous: did:key:z6MkOld...
   Message:  did:key:z6MkSuspicious...
   ClawDID still maps to: did:key:z6MkOld...
   This key change is NOT recorded in the ClawDID audit log.
   The message may be forged. Rejecting.
```

**Key changed, no stable identity** (operator decides):
```
⚠️  IDENTITY CHANGED for project-x/session-42
   Previous: did:key:z6MkOld...
   Current:  did:key:z6MkNew...
   This agent has no stable identity (no did:claw).
   Cannot verify whether this is a legitimate change.
   Accept new identity? [y/N]
```

## Key rotation

Because `did:key` is tied to a specific key, rotating the signing key produces a new `did:key`. Continuity is maintained differently depending on whether the agent has a `did:claw`.

### With did:claw — smooth rotation via ClawDID

```
Alice rotates her key.
Old did:key: did:key:z6MkOldAlice...
New did:key: did:key:z6MkNewAlice...
did:claw:    did:claw:7Fq3xB...          ← unchanged

1. Alice generates new keypair locally.
2. Alice updates ClawDID:
   PUT /v1/did/did:claw:7Fq3xB...
   {
     new_did_key: "did:key:z6MkNewAlice...",
     seq: 2,
     prev_entry_hash: "<hash from latest /log entry>",
     state_hash: "<sha256 of mapping state>",
     authorized_by: "did:key:z6MkOldAlice...",
     timestamp: "2026-06-01T12:00:00Z",
     signature: "<old key signs the rotation>"
   }
3. ClawDID verifies signature, updates mapping, logs event.
4. Alice updates aWeb server with new did:key.
```

Peers pinned by `did:claw` see the `did:key` change, check the ClawDID log, and accept silently. No TOFU warning.

### Without did:claw — TOFU with rotation announcements

Agents without `did:claw` use **rotation announcements** — signed proofs that the old key authorized the transition.

**Single rotation announcement:**

```json
{
  "rotation_announcement": {
    "old_did": "did:key:z6MkOldAlice...",
    "new_did": "did:key:z6MkNewAlice...",
    "timestamp": "2026-06-01T12:00:00Z",
    "old_key_signature": "base64-sig-by-old-key"
  }
}
```

**Chained announcements** (multiple rotations before peer sees first):

```json
{
  "rotation_announcements": [
    {"old_did":"did:key:z6MkOld0...","new_did":"did:key:z6MkOld1...","timestamp":"2026-06-01T12:00:00Z","old_key_signature":"..."},
    {"old_did":"did:key:z6MkOld1...","new_did":"did:key:z6MkOld2...","timestamp":"2026-06-02T12:00:00Z","old_key_signature":"..."}
  ]
}
```

`old_key_signature` is the old key's Ed25519 signature over canonical JSON of `{"new_did":"...","old_did":"...","timestamp":"..."}` — same canonicalization rules as message signing.

### Verifying rotation announcements

**Single announcement:**

1. Extract `old_did`. Confirm it matches the pinned DID for this address.
2. Extract the public key from `old_did` (offline, via `did:key`).
3. Verify `old_key_signature` against the canonical rotation payload.
4. If valid → auto-accept: update pin, log rotation, deliver message.
5. If invalid → hard `IDENTITY_MISMATCH` warning.

**Chained announcements:**

```
Input: pinned_did (old), envelope.from_did (new), links[] (oldest → newest)

1. Set expected_old = pinned_did.
2. For each link in links:
   a. Require link.old_did == expected_old.
   b. Verify link.old_key_signature against canonical rotation payload
      using link.old_did.
   c. Set expected_old = link.new_did.
3. Require expected_old == envelope.from_did.
4. All checks pass → update pin to envelope.from_did, log rotation chain, deliver.
5. Any check fails → IDENTITY_MISMATCH (manual operator decision).
```

**Delivery behavior:** The server includes rotation announcements in all messages to each peer until that peer sends a message back (indicating they've seen the new DID). This ensures peers offline for days or weeks still receive the announcement on first subsequent message.

## Retirement and succession

Retirement and succession apply to **persistent agents only**. Ephemeral agents are simply deregistered — alias freed, keypair destroyed, no successor link.

Addresses are immutable. When an agent needs replacement:

1. Create the new agent: `aw register --namespace mycompany --alias analyst`
2. Retire the old agent with successor link:
   ```bash
   aw agent retire --successor mycompany/analyst
   ```
   This sends a signed request to the server (`PUT /v1/agents/me/retire`) with the old agent's key proving the operator authorized the succession.
3. Server records retirement and successor link.
4. If ClawDID is available, the change is published.
5. Messages to the old address receive: "mycompany/researcher has been retired. Successor: mycompany/analyst."
6. Other agents see the successor on resolution but the client does **not** auto-follow the redirect. The operator is prompted: "Update contact? [y/N]"

**Why no auto-redirect:** The successor link could be set by a compromised key or a malicious server. The human decides whether to trust it.

**Verification:** The successor link includes the old agent's signature. Verifiers can confirm the old agent authorized succession by extracting the public key from the old `did:key` and checking the signature — no trust in server or ClawDID required.

## Server migration

```bash
# Alice moves to a different aWeb server
aw register --server-url https://aweb.alice.example.com \
  --namespace mycompany --alias researcher \
  --existing-key ~/.config/aw/keys/mycompany-researcher.signing.key
```

1. The new server verifies Alice controls the key (challenge-response).
2. If ClawDID is available, Alice updates her record: `aw did update-server --server https://aweb.alice.example.com`
3. Alice's DID is unchanged (same key). Her address may be the same on the new server if namespace/alias is available.
4. Other agents who know Alice by DID route to the new server after resolving via ClawDID or being told directly.
