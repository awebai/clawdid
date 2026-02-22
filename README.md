# clawdid

ClaWDID is an open-source mapping service and append-only audit log for stable agent identities.

It maps a stable identifier (e.g. `did:claw:...`) to the agent’s current `did:key:...` and publishes
an auditable history of changes (key rotations, server migrations).

This repo currently includes:
- Protocol source-of-truth docs: `sot.md`, `sot-2026-02-22-addendum-v2.md`
- Implementation: `backend/` (FastAPI + pgdbm/Postgres)

## Development

Prereqs:
- Python 3.12+
- PostgreSQL 15+

```bash
cd backend
uv sync
make dev-setup
make dev-backend
```

## Production

See `OPERATIONS.md`.

