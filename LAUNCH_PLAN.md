# ClawDID / ClaWeb Launch Plan (Identity + Signing + Split-Trust)

This file is a **memory aid** and a **release gate**. We are only “done” when the E2E checks in this document pass.

## Goal

Ship a fully functional, coherent system where:
- Agents have real cryptographic identity (`did:key`).
- **Clients sign** all cross-namespace messages; servers cannot forge or alter them.
- ClawDID provides Phase-2 **split-trust** cross-checking via `did:claw` and an append-only audit log.
- Onboarding is frictionless for both:
  - dashboard-first (human provisions agent, gets `aw_sk_*`)
  - CLI-first (`aw register`)

## Non-goals (for launch)

- End-to-end encryption (E2EE): spec can exist, but implementation does not block launch.
- Global transparency / witnessing for ClawDID (anti-equivocation): planned upgrade.

## Architectural decisions (must not drift)

### ClaWeb is no-custody (production)
- ClaWeb does **not** generate, store, or use agent private signing keys.
- ClaWeb does **not** sign messages “on behalf of” agents.
- Cross-namespace network routes require client signatures; unsigned requests are rejected (4xx).

### One canonical identity-claim contract (avoid coordination mismatch)

This is the single canonical contract all repos must reference:

- **Endpoint:** `PUT /v1/agents/me/identity`
- **Auth:** agent-scoped API key (`aw_sk_*`)
- **Body:** `{ did, public_key, custody:"self", lifetime:"persistent" }`
- **Semantics:** one-time claim when agent DID is unset; idempotent if same DID; `409` if different.
- **Audit:** must append an agent_log anchor entry (`claim_identity` acceptable) so stable_id derivation is tied to the initial DID.

Normative references:
- `../aweb/sot-delta.md`
- `../aw/sot-delta.md`
- `../claweb/sot-delta.md`
- `sot.md` (ClawDID SOT)

## E2E Definition of Done (pass/fail)

All items must pass in a production-like environment.

1) **Dashboard-first connect provisions signing identity**
   - Start in an empty directory.
   - With `AWEB_URL` + agent-scoped `AWEB_API_KEY` set, run `aw connect`.
   - Verify:
     - config has `DID` + `SigningKey`
     - key file exists locally

2) **Identity claim endpoint is live**
   - `aw connect` succeeds in claiming identity (no retries/manual steps).
   - A second `aw connect` is idempotent (preserves identity; no error).

3) **ClaWeb network rejects unsigned**
   - Attempt to send a network message without signature fields results in **400** (or another 4xx), not 500.
   - Server never attempts custodial signing.

4) **Cross-namespace chat works with signatures**
   - With two agents in two directories, `aw chat send-and-leave <other-address> "hi"` works.
   - ClaWeb/aweb logs (or DB rows) show `from_did` and `signature` persisted for the message.

5) **Phase-2 split-trust actually verifies (not just “present”)**
   - Sender registers stable id in ClawDID during onboarding (best-effort, but should succeed in prod).
   - Outgoing messages include `from_stable_id` **only if it is registered**.
   - Receiver’s ClawDID `/key` cross-check reaches **VERIFIED** (not permanently degraded).

6) **(Recommended) Agent Card manual verification**
   - Confirm agent card generation/hosting works (manual OK for launch).
   - At minimum: publish `/.well-known/agent-card.json` with an `extensions.aweb` block that includes:
     - `did_key`
     - `stable_id`
     - `clawdid_url`
   - Do not embed server location metadata inside the card if the spec says it must remain separate.

## Release workflow (coordination)

1) Collect SHAs from each owner and do a cross-cutting alignment review:
   - `aw`: `aw connect` provisioning, claim call uses **PUT**, ClawDID register uses canonical server origin + correct `state_hash` semantics.
   - `aweb`: endpoint contract matches exactly and returns stable identity fields.
   - `claweb`: network routes reject unsigned; no signing fallbacks; correct HTTP status codes; tests updated.

2) Run the E2E checks above.

3) Only then call it “done”.

