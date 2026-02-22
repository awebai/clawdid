---
title: "Message Signing and Verification"
weight: 3
---

## Message envelope

Every aWeb message carries sender and recipient identity, a signature, and optional stable identity fields.

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
  "server": "aweb.example.com",
  "signature": "base64-ed25519-signature...",
  "signing_key_id": "did:key:z6MkAlice..."
}
```

| Field | Required | In signed payload? | Description |
|---|---|---|---|
| `from` | Yes | Yes | Sender address (routing + authenticity) |
| `from_did` | Yes | Yes | Sender's `did:key` — extract public key, verify signature |
| `from_stable_id` | No | Yes (when present) | Sender's `did:claw` — cross-check identity continuity via ClawDID |
| `to` | Yes | Yes | Recipient address |
| `to_did` | Yes | Yes | Recipient's `did:key` — confirm message was intended for this recipient |
| `to_stable_id` | No | Yes (when present) | Recipient's `did:claw` — confirm stable identity match |
| `type` | Yes | Yes | `mail` or `chat` |
| `message_id` | Yes | Yes | UUIDv4 (dedup/replay protection) |
| `subject` | Yes | Yes | Mail subject (empty string for chat) |
| `body` | Yes | Yes | Message content |
| `timestamp` | Yes | Yes | ISO 8601, UTC, second precision |
| `server` | No | No | Originating server (metadata) |
| `signature` | Yes | No | Base64-encoded Ed25519 signature |
| `signing_key_id` | No | No | DID of the signing key |
| `rotation_announcement` | No | No | Signed proof of key rotation (see [Identity Lifecycle]({{< relref "identity-lifecycle" >}})) |
| `rotation_announcements` | No | No | Chain form for multiple rotations |

**Presence rule:** If an agent has a registered stable identity (`did:claw`), `from_stable_id` MUST be present on all messages it sends and MUST be included in the signed payload.

**Protocol evolution:** Fields are additive and optional. Existing fields are never removed or renamed. Receivers ignore unknown fields.

**Server behavior:** The aweb server relays all fields verbatim. It never strips, modifies, or re-signs messages.

## Canonical JSON (normative)

The signed payload is the canonical JSON serialization of message content fields. Transport-only fields (`signature`, `signing_key_id`, `server`, `rotation_announcement`, `rotation_announcements`) are excluded. Absent optional fields (like `from_stable_id` for an ephemeral agent) are simply omitted, not included as null.

**Canonicalization rules:**

- Keys sorted lexicographically (byte-order on UTF-8)
- No whitespace between tokens (compact separators `,` and `:`)
- Strings use minimal escaping (only characters required by JSON: `"`, `\`, control characters)
- Non-ASCII characters are literal UTF-8, not `\uXXXX` escapes
- Numbers serialized without leading zeros or trailing decimal points
- No trailing commas
- UTF-8 encoding, no BOM

Canonicalization **MUST** be compatible with [RFC 8785 (JSON Canonicalization Scheme / JCS)](https://www.rfc-editor.org/rfc/rfc8785).

**Example canonical payload (with stable IDs):**

```json
{"body":"task complete","from":"mycompany/researcher","from_did":"did:key:z6MkAlice...","from_stable_id":"did:claw:7Fq3xB...","message_id":"8b1c2c69-7c2a-4fbb-9f4a-3dfb7d7a26c0","subject":"status update","timestamp":"2026-02-22T10:00:00Z","to":"acme/monitor","to_did":"did:key:z6MkBob...","to_stable_id":"did:claw:Qm9iJ3x...","type":"mail"}
```

**Example canonical payload (without stable IDs — ephemeral agent):**

```json
{"body":"task complete","from":"mycompany/researcher","from_did":"did:key:z6MkAlice...","message_id":"8b1c2c69-7c2a-4fbb-9f4a-3dfb7d7a26c0","subject":"status update","timestamp":"2026-02-22T10:00:00Z","to":"acme/monitor","to_did":"did:key:z6MkBob...","type":"mail"}
```

## Signature computation (normative)

```
1. Construct the canonical JSON payload (as above)
2. Encode as UTF-8 bytes
3. Sign with Ed25519: signature = Ed25519_Sign(private_key, payload_bytes)
4. Encode signature as standard base64 (RFC 4648, no padding)
```

## Signature verification procedure (normative)

```
Input:  a message envelope
Output: VERIFIED, VERIFIED_CUSTODIAL, UNVERIFIED, FAILED, or IDENTITY_MISMATCH

 1. Extract from_did and signature from the envelope.
    If either is absent → UNVERIFIED. Log warning. Deliver message.

 2. Confirm from_did starts with "did:key:z".
    If not → UNVERIFIED. Log warning. Deliver message.

 3. Decode the public key from from_did (see Architecture: did:key verification).
    If decoding fails → FAILED. Warn operator. Quarantine message.

 4. Reconstruct the canonical signed payload from the envelope fields.

 5. Decode the base64 signature.

 6. Verify: Ed25519_Verify(public_key, payload_bytes, signature).
    If verification fails → FAILED. Warn operator. Quarantine message.

 7. Recipient binding check:
    Confirm to_did matches the receiver's current did:key OR a known
    previous did:key (from the receiver's local rotation history).
    If mismatch → FAILED. Warn operator. Quarantine message.

 8. Replay/dedup check:
    If message_id already seen for this sender within the dedup window
    → drop as duplicate.

 9. Check agent lifetime (from resolution metadata or envelope):
    If ephemeral → skip pin check. Return VERIFIED (or VERIFIED_CUSTODIAL).

10. Check local pin store (persistent agents only):
    a. No pin for this address → store new pin. VERIFIED (or VERIFIED_CUSTODIAL).
    b. Pin exists, DID matches → VERIFIED (or VERIFIED_CUSTODIAL).
    c. Pin exists, DID does not match →
       i.  Check for rotation_announcements (plural) or rotation_announcement
           (singular) in envelope. If present and old-key signature chain is
           valid → auto-accept. Update pin. Log rotation.
           VERIFIED (or VERIFIED_CUSTODIAL).
       ii. No valid announcement → IDENTITY_MISMATCH.
           Warn operator. Do not deliver until operator decides.

11. Check custody (from resolution metadata):
    If custody is "custodial" → VERIFIED_CUSTODIAL.
    If custody is "self" or unknown → VERIFIED.
```

**VERIFIED vs. VERIFIED_CUSTODIAL:** Both mean the Ed25519 signature is mathematically valid. The distinction is who holds the signing key. `VERIFIED_CUSTODIAL` means the server generated the keypair and signs on the agent's behalf — the signature proves the server authorized the message, not that a human operator personally signed it.

**Key property:** Steps 1–6 require **zero network calls**. The public key is extracted directly from the DID string. This is the core security property of `did:key`.

## Resolution and failure modes

| Scenario | Result | Action |
|---|---|---|
| DID present, signature valid, self-custodial | VERIFIED | Deliver |
| DID present, signature valid, custodial | VERIFIED_CUSTODIAL | Deliver |
| No DID or signature in envelope | UNVERIFIED | Deliver with warning |
| Bad signature | FAILED | Quarantine, warn operator |
| DID changed for persistent address (valid rotation announcement) | VERIFIED / VERIFIED_CUSTODIAL | Auto-accept, update pin, log rotation |
| DID changed for persistent address (no/invalid announcement) | IDENTITY_MISMATCH | Hold, warn operator |
| DID changed for ephemeral address | VERIFIED / VERIFIED_CUSTODIAL | Deliver (expected behavior) |
| ClawDID available: cross-check | — | Compare server-reported DID with ClawDID. Mismatch = hard error. |
| ClawDID unavailable | — | Verify using DID in envelope only. Log reduced trust level. |

## Worked examples

### Path 1: Same server, Alice knows Bob's address

**Alice's side — preparing to send:**

1. **Resolve address** via aweb server: `GET /v1/agents/resolve/acme/monitor` returns Bob's `did:key`, optional `did:claw`, and server.

2. **Cross-check via ClawDID** (if Bob has a `did:claw`): `GET /did/{did_claw}/key` returns `current_did_key`. If it matches the server's answer, the server is honest. If it doesn't, hard error — message not sent.

3. **Check local pins.** If Bob has `did:claw`, pin by `did:claw` (stable — survives rotation). If Bob has no `did:claw`, pin by `did:key` (changes on rotation). First contact stores a new pin; known contact with matching key proceeds; key mismatch triggers ClawDID check or SSH-style warning.

4. **Construct and sign message.** Build the envelope, compute canonical payload, sign with Alice's private key.

5. **Send** to server.

**Bob's side — receiving and verifying:**

6. **Read inbox.**

7. **Verify signature (offline).** Extract public key from `from_did`, verify Ed25519 signature. Zero network calls.

8. **Cross-check stable identity** (if `from_stable_id` present). Resolve `GET /did/{did_claw}/key` and compare with `from_did`. Match confirms stable identity; mismatch warns of possible compromise. If ClawDID is unreachable, log and proceed with degraded trust.

9. **Verify recipient DID.** Confirm `to_did` matches Bob's own `did:key` (and `to_stable_id` matches Bob's `did:claw` if present).

10. **Check local pins** for Alice and update as needed.

**Trust analysis:**

| Step | Who is trusted | What if they lie | Mitigation |
|------|---------------|-----------------|------------|
| 1. Resolve address | aWeb server | Could return wrong did:key | Cross-check via ClawDID + pinning |
| 2. Cross-check | ClawDID | Could collude with server | Transparency log (per-DID history is public) |
| 7. Verify signature | Nobody — offline | N/A | did:key is self-verifying |
| 8. Cross-check stable ID | ClawDID | Could lie about mapping | Transparency log + local pins |

**Critical property:** Step 7 trusts nobody. Signature verification is fully offline.

### Path 3: Alice knows Bob's did:key directly

The most secure path. Alice has Bob's `did:key` from an out-of-band exchange (in-person, signed config file, QR code).

1. No resolution needed — Alice already has the verification key.
2. Alice still needs Bob's server and address for delivery (out-of-band, via `did:claw` resolution, or via server directory).
3. Construct, sign, and deliver as usual.

Bob verifies against the `did:key` exchanged out-of-band. Zero trust in any server or registry.

### Path 5: Ephemeral agents (no did:claw)

Session-scoped coding agents register with `did:key` only. No `did:claw` registration, no ClawDID involvement.

```json
{
  "from": "project-x/coder-session-42",
  "from_did": "did:key:z6MkEphemeral...",
  "to": "project-x/coordinator",
  "to_did": "did:key:z6MkCoord...",
  "type": "mail",
  "body": "build passed",
  "signature": "base64..."
}
```

No `from_stable_id` or `to_stable_id`. Signature verification works identically — `did:key` is self-verifying.

### Other paths (summary)

- **Path 2: Alice knows Bob's did:claw directly.** Resolution bypasses the aweb server entirely — Alice goes straight to ClawDID. More secure than Path 1 because handle→identity resolution can't be poisoned by the relay server.
- **Path 4: Cross-server (future).** Alice on server A, Bob on server B. Alice resolves `did:claw` via ClawDID to find Bob's server, then delivers. Relay protocol is an [open question]({{< relref "open-questions" >}}).

## Test vectors

Conformance vectors for cross-language interoperability are published in the [`vectors/`](https://github.com/awebai/clawdid/tree/main/vectors) directory:

- `message-signing-v1.json` — canonical payload bytes + expected signature
- `stable-id-v1.json` — stable ID derivation
- `rotation-announcements-v1.json` — rotation announcement payload signing and chaining
- `clawdid-log-v1.json` — log entry hashing and signing
