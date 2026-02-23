# ClawDID Operations Manual

This document describes how to deploy, verify, observe, and debug `clawdid` in production.

## What Runs In Production

- **Single container** (`clawdid`) serving the API
- **Managed dependency**
  - Postgres (required)
- **Image registry**
  - GHCR: `ghcr.io/awebai/clawdid`
- **Host**
  - Render Web Service (image-based deploy)

## Required Endpoints (Ops Contract)

- `GET /live`
  - Always `200` if the process is running.
  - Does not check Postgres.
- `GET /ready`
  - `200` only if Postgres is reachable.
  - Used as the health check.
- `GET /health`
  - Human-friendly status summary; includes dependency statuses and build identity.
- `GET /meta`
  - Lightweight public build metadata.
- `GET /api/v1/release` (no auth)
  - Source of truth for "what is running"; includes build identity.

## Verify A Deploy (No Guessing)

After deploy finishes, verify against the production API hostname (expected: `https://api.clawdid.ai`):

1. Verify build identity:
   - `curl -fsS https://api.clawdid.ai/api/v1/release | jq .`
2. Verify readiness:
   - `curl -fsS https://api.clawdid.ai/ready | jq .`
3. Verify OpenAPI:
   - `curl -fsS https://api.clawdid.ai/openapi.json | jq '.info.title,.info.version'`

## Environment Variables

The authoritative list is `backend/.env.production.example`.

Minimum required in production:
- `DATABASE_URL`
- `ENVIRONMENT=production`

Recommended:
- `LOG_JSON=true`
- `LOG_LEVEL=INFO`
- `TRUST_PROXY_HEADERS=true`
- `CORS_ALLOWED_ORIGINS=["https://app.clawdid.ai","https://clawdid.ai"]`

Rate limiting is always active. Backend defaults to in-memory (single instance).
For multi-instance deploys:
- `RATE_LIMIT_BACKEND=redis` and `RATE_LIMIT_REDIS_URL=redis://...`
- If you already have a WAF (Cloudflare/Render/ALB), prefer edge rate limiting and keep app-level limits as a backstop.

## Database

Render Postgres provides daily automatic backups. RPO assumption: up to 24 hours of identity registrations/rotations may be lost on full DB failure. RTO: create a new Render Postgres instance, restore from backup, update `DATABASE_URL`, redeploy — migrations auto-apply on startup.

For horizontal scaling: total Postgres connections = `pool_size × instances`. Monitor and adjust pool size or use PgBouncer if needed.

## Frontend (SPA) Build

The SPA is a static Vite build deployed separately (e.g. at `app.clawdid.ai`).

Build for production:
```
cd frontend
VITE_CLAWDID_API_BASE=https://api.clawdid.ai npm run build
```

Output goes to `frontend/dist/`. Deploy as static files.

If `VITE_CLAWDID_API_BASE` is not set, the SPA defaults to `http://127.0.0.1:18111` (local dev).
