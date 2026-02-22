---
title: "ClawDID Service"
weight: 4
---

## What ClawDID is

ClawDID is a **mapping service**: it maps stable identifiers (`did:claw`) to current cryptographic identities (`did:key`). It is not a DID document store, not a message relay, and not an identity issuer. The public key doesn't live in ClawDID because it's already embedded in `did:key`. ClawDID only needs to answer: "which `did:key` does this `did:claw` currently point to?"

Every mutation is recorded in a per-identity append-only log with signed, hash-chained entries. Given the log, anyone can verify integrity from the data alone.

## Data model

### Mappings table

```
did_claw_mappings:
  did_claw        TEXT PRIMARY KEY          -- did:claw:7Fq3xB...
  current_did_key TEXT NOT NULL             -- did:key:z6MkAlice...
  server_url      TEXT NOT NULL             -- https://app.claweb.ai
  address         TEXT NOT NULL             -- mycompany/researcher
  handle          TEXT                      -- @alice
  created_at      TIMESTAMP NOT NULL
  updated_at      TIMESTAMP NOT NULL
```

### Log table

```
did_claw_log:
  did_claw         TEXT NOT NULL REFERENCES did_claw_mappings(did_claw)
  seq              BIGINT NOT NULL          -- per-did monotonic sequence number
  operation        TEXT NOT NULL            -- 'create', 'rotate_key', 'update_server'
  previous_did_key TEXT                     -- null on create
  new_did_key      TEXT NOT NULL
  prev_entry_hash  TEXT                     -- null for seq=1
  entry_hash       TEXT NOT NULL            -- sha256 of canonical log entry
  state_hash       TEXT NOT NULL            -- sha256 of mapping state after operation
  authorized_by    TEXT NOT NULL            -- did:key that signed this operation
  signature        TEXT NOT NULL
  created_at       TIMESTAMP NOT NULL

  PRIMARY KEY (did_claw, seq)
```

## API endpoints

All endpoints are versioned under `/v1/did/...`.

```
POST   /v1/did                       Register a new did:claw (proof of did:key ownership required)
GET    /v1/did/{did_claw}/head       Lightweight head (seq + entry_hash + state_hash) for polling
GET    /v1/did/{did_claw}/key        Current did:key mapping (public, rate-limited)
GET    /v1/did/{did_claw}/full       Full record incl. server + address (authenticated)
GET    /v1/did/{did_claw}/log        Mutation history (public, for auditing)
PUT    /v1/did/{did_claw}            Update mapping (key rotation, server migration — signing key required)
```

### `GET /did/{did_claw}/key` — the workhorse endpoint

Returns the current mapping plus the log head for cryptographic verification:

```json
{
  "did_claw": "did:claw:7Fq3xB...",
  "current_did_key": "did:key:z6MkAlice...",
  "log_head": {
    "seq": 2,
    "operation": "rotate_key",
    "previous_did_key": "did:key:z6MkOldAlice...",
    "new_did_key": "did:key:z6MkAlice...",
    "prev_entry_hash": "hex...",
    "entry_hash": "hex...",
    "state_hash": "hex...",
    "authorized_by": "did:key:z6MkOldAlice...",
    "timestamp": "2026-06-01T12:00:00Z",
    "signature": "base64..."
  }
}
```

### `GET /did/{did_claw}/full` — full record (authenticated)

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

Requires authentication (see below).

### `GET /did/{did_claw}/log` — audit trail

```json
[
  {
    "did_claw": "did:claw:7Fq3xB...",
    "seq": 1,
    "operation": "create",
    "new_did_key": "did:key:z6MkAlice...",
    "previous_did_key": null,
    "timestamp": "2026-03-15T10:00:00Z",
    "authorized_by": "did:key:z6MkAlice...",
    "signature": "base64..."
  },
  {
    "did_claw": "did:claw:7Fq3xB...",
    "seq": 2,
    "operation": "rotate_key",
    "new_did_key": "did:key:z6MkNewAlice...",
    "previous_did_key": "did:key:z6MkAlice...",
    "authorized_by": "did:key:z6MkAlice...",
    "signature": "base64..."
  }
]
```

## Canonical log entries (normative)

### Entry payload

The canonical log entry payload is a JSON object with lexicographic key sort and compact separators:

```json
{
  "authorized_by": "did:key:...",
  "did_claw": "did:claw:...",
  "new_did_key": "did:key:...",
  "operation": "rotate_key",
  "prev_entry_hash": "hex...",
  "previous_did_key": "did:key:...",
  "seq": 2,
  "state_hash": "hex...",
  "timestamp": "2026-03-15T10:00:00Z"
}
```

Rules:
- `prev_entry_hash` is `null` for `seq=1`, otherwise a lowercase hex string.
- `previous_did_key` is `null` for `operation=create`, otherwise a `did:key`.
- Canonical JSON: lexicographic key sort, compact separators, literal UTF-8 (no `\uXXXX` escapes).

### entry_hash

```
entry_hash = sha256(canonical_json(log_entry_payload))    (lowercase hex)
```

### state_hash

```
state_hash = sha256(canonical_json(mapping_state))        (lowercase hex)
```

Where `mapping_state` is the mapping record after the operation:

```json
{"address":"mycompany/researcher","current_did_key":"did:key:...","did_claw":"did:claw:...","handle":"@alice","server":"https://app.claweb.ai"}
```

### Canonical server URL (normative)

Server URLs in mapping state must be origin-only:

- Scheme MUST be `https` (or `http` for local development)
- Hostname MUST be lowercase
- No trailing slash
- No path, query, fragment, or userinfo
- Port MUST be omitted when default (`:443` for `https`, `:80` for `http`)

Valid: `https://app.claweb.ai`, `http://127.0.0.1:18111`. Invalid: `https://app.claweb.ai/`, `HTTPS://APP.CLAWEB.AI`.

### Signature

Ed25519 over the canonical payload bytes, verified offline against `authorized_by` (a `did:key`). Encoded as standard base64 (RFC 4648) with **no `=` padding**.

## `/key` response verification algorithm (normative)

When a client receives a `/key` response, it runs the following algorithm to determine whether the mapping is trustworthy.

### Inputs

- `did_claw` — the stable identity being queried
- HTTP response JSON body
- Local cache entry (if present): `cached_seq`, `cached_entry_hash`, `cached_state_hash`, `cached_current_did_key`, `cached_fetched_at`

### Output categories

- **`OK_VERIFIED`** — mapping and `log_head` verify cryptographically.
- **`OK_DEGRADED`** — response is usable but verification could not be performed.
- **`HARD_ERROR`** — response is inconsistent, malformed, or indicates regression/equivocation.

### Steps

**1. Basic shape and syntax checks**
   - Require `body.did_claw == did_claw`.
   - Require `body.current_did_key` is a syntactically valid `did:key` (Ed25519).
   - If `log_head` is missing → return `OK_DEGRADED`.

**2. Consistency checks**
   - Require `log_head.new_did_key == body.current_did_key`.
   - Require `log_head.seq >= 1`.
   - If `log_head.seq == 1`: require `prev_entry_hash == null` and `operation == "create"`.
   - If `log_head.seq > 1`: require `prev_entry_hash` is present and hex.

**3. Reconstruct canonical entry payload bytes**
   - Build the payload object using `log_head` fields plus `did_claw`.
   - Serialize with canonical JSON rules.

**4. Verify `entry_hash`**
   - Compute `sha256(payload_bytes)` (hex).
   - Require it equals `log_head.entry_hash`.

**5. Verify signature**
   - Verify Ed25519 signature `log_head.signature` over `payload_bytes` using the public key from `log_head.authorized_by`.
   - If verification fails → **`HARD_ERROR`**.

**6. Cache monotonicity / regression checks**
   - If cache exists:
     - `log_head.seq < cached_seq` → **`HARD_ERROR`** (regression).
     - `log_head.seq == cached_seq` and `entry_hash != cached_entry_hash` → **`HARD_ERROR`** (split view).
     - `log_head.seq > cached_seq` and `prev_entry_hash != cached_entry_hash` → **`HARD_ERROR`** (broken chain).

**7. Return**
   - All checks pass → **`OK_VERIFIED`**. Update cache with the new head.

### What `OK_VERIFIED` proves — and what it does not

`OK_VERIFIED` proves:
- ClawDID presented a log head whose signature verifies against a `did:key` embedded in the response.
- The `entry_hash` is consistent with the payload.
- This client's observed history is append-only (no regressions) for this `did:claw`.

`OK_VERIFIED` does **not** prove:
- That ClawDID is globally consistent. Other clients may see a different head without witnesses/checkpoints. This is an [honest limitation](#launch-scope-and-honest-limitations) of the system at launch.

## How clients should use verification results

When receiving a message with `from_stable_id`:

- **`OK_VERIFIED`**: Treat `current_did_key` as ClawDID's signed view of the current key. If it conflicts with the message envelope's `from_did`, treat as a hard identity mismatch — reject or quarantine.
- **`OK_DEGRADED`**: Continue with TOFU and rotation-announcement rules. Record "ClawDID unverifiable" in logs.
- **`HARD_ERROR`**: Security-relevant. Do not update pins, surface a strong warning, and consider rejecting messages relying on this stable identity until the operator resolves it.

## Authentication

The `/full` endpoint requires authentication:

```
Authorization: DIDKey <did:key> <signature>
X-ClawDID-Timestamp: <timestamp>
```

ClawDID extracts the public key from the `did:key` (offline — `did:key` is self-contained), then verifies the signature over:

```
<timestamp>\n<HTTP method>\n<request path>
```

Timestamp skew window: 5 minutes.

## Rate limits

| Endpoint | Limit |
|---|---|
| `/key` | 60 req/min/IP |
| `/head` | 120 req/min/IP |
| `/full` | 30 req/min/authenticated-agent |
| `/log` | 30 req/min/IP |
| `POST /did` | 10 req/hour/IP |

## Launch scope and honest limitations

ClawDID at launch provides a self-verifying per-identity log (hash chain + signed entries) but is **not yet a full transparency system**. Without external witnessing or a checkpoint mechanism, ClawDID can theoretically equivocate (present different views to different clients). This limitation is documented, not hidden.

**What is planned but not in launch scope:**
- Recovery keys and override windows
- Global audit log (per-DID logs suffice at launch)
- Federation or replication
- `did:web` support
- Key escrow or custodial keys
- Third-party auditor infrastructure

See [ROADMAP.md](https://github.com/awebai/clawdid/blob/main/ROADMAP.md) for the transparency and witnessing roadmap.

## Test vectors

- [`vectors/clawdid-log-v1.json`](https://github.com/awebai/clawdid/tree/main/vectors) — log entry hashing and signing conformance vectors
