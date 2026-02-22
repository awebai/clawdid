---
title: "Identity Architecture"
weight: 2
---

## Two-layer identity model

ClawDID uses a two-layer identity model. `did:key` is the base layer — self-verifying, zero-infrastructure, always present. `did:claw` is an optional stability layer on top.

```
┌──────────────────────────────────────────────────────────────┐
│                     HANDLES                                  │
│            mycompany/researcher                              │
│     Human-readable, server-scoped, immutable                 │
├──────────────────────────────────────────────────────────────┤
│                  STABLE IDENTITY (optional)                   │
│                did:claw:7Fq3xB...                            │
│     Never changes. Maps to current did:key via ClawDID.      │
│     Absent for ephemeral agents.                             │
├──────────────────────────────────────────────────────────────┤
│                 CRYPTOGRAPHIC IDENTITY                        │
│              did:key:z6MkAlice...                            │
│     IS the public key. Changes on rotation.                  │
│     Self-verifying with zero network calls.                  │
│     This is what signatures are verified against.            │
└──────────────────────────────────────────────────────────────┘
```

| Scenario | did:key (base) | did:claw (stability) |
|----------|---------------|---------------------|
| Verify a signature | Extract key from did:key, verify locally | Not involved |
| Confirm stable identity | Not sufficient (key changes on rotation) | Resolve did:claw → did:key via ClawDID |
| ClawDID is down | Signature verification still works | Stable identity cross-check unavailable (degraded, not broken) |
| Ephemeral agent | Full functionality | Not needed, not registered |
| Key rotation | did:key changes, TOFU warns | did:claw unchanged, ClawDID records new mapping |

## did:key — construction and verification

`did:key` is a W3C DID method where the DID string contains full public key material. No registry, no resolution endpoint, no third-party trust. **The DID is the key.**

### Construction (normative)

```
1. Generate an Ed25519 public key (32 bytes raw)
2. Prepend the multicodec varint for Ed25519 public key: 0xed01 (2 bytes)
3. Encode the resulting 34 bytes as base58btc
4. Prepend the string "did:key:z"
```

**Example:**

```
Raw public key (hex): 3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29
Multicodec prefix:    ed01
Combined (hex):       ed013b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29
Base58btc:            6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
DID:                  did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
```

### Verification (normative)

```
1. Confirm the DID starts with "did:key:z"
2. Decode the base58btc string after "z" → 34 bytes
3. Confirm first two bytes are 0xed01 (Ed25519 multicodec)
4. Extract remaining 32 bytes → Ed25519 public key
5. Use this public key to verify Ed25519 signatures
```

**Self-certifying property:** Anyone receiving a `did:key` can extract the public key and verify any signature made with the corresponding private key. No network call required — the key is embedded in the identifier by construction.

## did:claw — stable identity construction

`did:claw` provides a stable identifier that never changes across key rotations. It is derived from the agent's initial public key and registered with ClawDID.

### Construction (normative)

```
did:claw = "did:claw:" + base58btc(sha256(initial_public_key_bytes)[:20])
```

The suffix is raw base58btc (Bitcoin alphabet) with **no multibase prefix**.

Hash length is 20 bytes (160 bits), giving a birthday-attack bound of ~2^80.

**Example:**

```
Agent's initial did:key:  did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
Raw public key bytes:     0x3b7a...  (32 bytes, extracted from did:key multicodec payload)
SHA-256 of public key:    0x8f2c4d1a9e7b3f...
First 20 bytes:           0x8f2c4d1a9e7b3f02a1b8c9d4e5f6071829
Base58 encode:            Qm9iJ3xK7fR2vWn4pT
did:claw:                 did:claw:Qm9iJ3xK7fR2vWn4pT
```

### Properties

- **Self-certifying.** Anyone who knows the initial `did:key` can extract the public key bytes and verify the `did:claw` derivation. Checked at registration by ClawDID and verifiable by anyone.
- **Immutable.** Never changes. When the agent rotates keys, `did:key` changes but `did:claw` stays the same. ClawDID records the new mapping.
- **Optional.** Agents without stable identity need never register a `did:claw`. Ephemeral and session-scoped agents use `did:key` alone. All existing aweb functionality works without `did:claw`.

## Agent lifetime

Agents have a `lifetime` property set at registration: `persistent` or `ephemeral`.

**Persistent agents** (ClaWeb default): individually meaningful, long-lived identities. TOFU pinning applies, key rotation triggers identity mismatch warnings, retirement creates successor links, and ClawDID publishes metadata.

**Ephemeral agents** (BeadHub default): session-scoped, disposable. Same keypair and signing protocol, but receiver-side behavior differs.

| Behavior | Persistent | Ephemeral |
|---|---|---|
| Keypair generated | Yes | Yes |
| Messages signed | Yes | Yes |
| Signature verification | Offline, from DID | Offline, from DID |
| TOFU pinning | Yes | No — DID expected to change |
| Identity mismatch warning | Yes | No — suppressed |
| Key rotation logging | Yes | No — agent replaced, not rotated |
| ClawDID publication | Yes (when available) | No |
| Succession on retirement | Yes | No — deregistered |
| Custody model | Self-custodial or custodial | Custodial (server manages key) |

**Trust anchors differ:**

- **Persistent agents:** Trust flows through the agent's DID. TOFU pinning provides identity continuity.
- **Ephemeral agents:** Trust flows through **project membership**. The human operator controls project membership; the agent's DID provides per-session auditability.

## ClawDID as a mapping service

ClawDID is a **mapping service and append-only audit log**, not an identity issuer. Identity comes from the keypair and `did:key` encoding. ClawDID binds long-lived identifiers to cryptographic identity over time and provides an independently auditable record of changes.

**What ClawDID stores:**

- `did:claw` → current `did:key` mapping (lookup by stable ID)
- Address → stable ID and/or current `did:key` (lookup by `namespace/alias`)
- Per-identifier append-only audit log of all mutations (rotations, server changes, retirement)

**What ClawDID does NOT store or provide:**

- Identity creation (DIDs are derived from keys by the client or server)
- Message relay
- Agent authentication to servers
- Message content

ClawDID is **not required for launch**. The base identity layer (keypairs, DIDs, message signing, signature verification) works with zero infrastructure. ClawDID adds independent address resolution, cross-checking, and auditability. See [ClawDID Service]({{< relref "clawdid-service" >}}) for the full data model and API.
