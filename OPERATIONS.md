# ClaWDID Operations Manual

This document describes how to deploy, verify, observe, and debug `clawdid` in production.

## What Runs In Production

- **Single container** (`clawdid`) serving the API
- **Managed dependency**
  - Postgres (required)
- **Image registry**
  - GHCR: `ghcr.io/awebai/clawdid`
- **Host**
  - Render Web Service (image-based deploy) via `render.yaml`

## Required Endpoints (Ops Contract)

- `GET /live`
  - Always `200` if the process is running.
  - Does not check Postgres.
- `GET /ready`
  - `200` only if Postgres is reachable.
  - Used as the Render health check.
- `GET /health`
  - Human-friendly status summary; includes dependency statuses and build identity.
- `GET /meta`
  - Lightweight public build metadata.
- `GET /api/v1/release` (no auth)
  - Source of truth for “what is running”; includes build identity.

## Verify A Deploy (No Guessing)

After deploy finishes, verify against the production hostname (expected: `https://clawdid.ai`):

1. Verify build identity:
   - `curl -fsS https://clawdid.ai/api/v1/release | jq .`
2. Verify readiness:
   - `curl -fsS https://clawdid.ai/ready | jq .`
3. Verify OpenAPI:
   - `curl -fsS https://clawdid.ai/openapi.json | jq '.info.title,.info.version'`

## Environment Variables

The authoritative list is `backend/.env.production.example`.

Minimum required in production:
- `DATABASE_URL`
- `ENVIRONMENT=production`

Recommended:
- `LOG_JSON=true`
- `LOG_LEVEL=INFO`
- `TRUST_PROXY_HEADERS=true`
