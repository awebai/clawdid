from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from clawdid.config import settings
from clawdid.db import DatabaseInfra, get_db_infra
from clawdid.did import (
    did_claw_from_public_key,
    public_key_from_did_key,
    stable_method_from_id,
    validate_stable_id,
)
from clawdid.models import (
    DidFullResponse,
    DidHeadResponse,
    DidKeyEvidence,
    DidKeyResponse,
    DidLogEntry,
    DidRegisterRequest,
    DidUpdateRequest,
)
from clawdid.ratelimit import rate_limit_dep
from clawdid.signing import canonical_json_bytes, verify_did_key_signature

router = APIRouter(prefix="/did", tags=["did"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_rfc3339(ts: str) -> datetime:
    # Accept "Z" suffix for UTC.
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone offset (e.g. Z or +00:00)")
    if dt.microsecond != 0:
        # SOT requires second precision to avoid cross-implementation drift.
        raise ValueError("timestamp must be second precision (no fractional seconds)")
    return dt.astimezone(timezone.utc)


def _enforce_timestamp_skew(ts: str) -> None:
    dt = _parse_rfc3339(ts)
    delta = abs((_now() - dt).total_seconds())
    if delta > settings.auth_timestamp_skew_seconds:
        raise ValueError("timestamp outside allowed skew window")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_server_origin(server_url: str) -> str:
    server_url = server_url.strip()
    if not server_url:
        raise ValueError("server URL must be non-empty")
    parsed = urlparse(server_url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("server URL scheme must be http or https")
    if parsed.username or parsed.password:
        raise ValueError("server URL must not include userinfo")
    if parsed.query or parsed.fragment:
        raise ValueError("server URL must not include query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("server URL must not include a path (origin only)")
    if not parsed.hostname:
        raise ValueError("server URL must include a host")

    host = parsed.hostname.lower()
    # urlparse() removes brackets for IPv6; add them back for serialization.
    host_out = f"[{host}]" if ":" in host and not host.startswith("[") else host

    port = parsed.port
    default_port = 80 if scheme == "http" else 443
    port_out = None if port in (None, default_port) else port
    return f"{scheme}://{host_out}{f':{port_out}' if port_out is not None else ''}"


def _require_canonical_server_origin(server_url: str) -> str:
    canonical = _canonical_server_origin(server_url)
    if server_url != canonical:
        raise ValueError(
            f"server URL must be canonical origin form: {canonical} (no trailing slash, no path, lowercase host)"
        )
    return canonical


def _log_entry_payload(
    *,
    did_claw: str,
    seq: int,
    operation: str,
    previous_did_key: str | None,
    new_did_key: str,
    prev_entry_hash: str | None,
    state_hash: str,
    authorized_by: str,
    timestamp: str,
) -> bytes:
    return canonical_json_bytes(
        {
            "authorized_by": authorized_by,
            "did_claw": did_claw,
            "new_did_key": new_did_key,
            "operation": operation,
            "prev_entry_hash": prev_entry_hash,
            "previous_did_key": previous_did_key,
            "seq": seq,
            "state_hash": state_hash,
            "timestamp": timestamp,
        }
    )


def _state_hash(
    *,
    did_claw: str,
    current_did_key: str,
    server: str,
    address: str,
    handle: str | None,
) -> str:
    payload = canonical_json_bytes(
        {
            "address": address,
            "current_did_key": current_did_key,
            "did_claw": did_claw,
            "handle": handle,
            "server": server,
        }
    )
    return _sha256_hex(payload)


@router.post("", dependencies=[Depends(rate_limit_dep("did_register"))])
async def register_did(
    req: DidRegisterRequest,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> dict:
    try:
        validate_stable_id(req.did_claw)
        _enforce_timestamp_skew(req.timestamp)
        canonical_server = _require_canonical_server_origin(req.server)
        if req.seq != 1 or req.prev_entry_hash is not None:
            raise ValueError("seq must be 1 and prev_entry_hash must be null on create")
        if req.authorized_by != req.did_key:
            raise ValueError("authorized_by must equal did_key on create")
        method = stable_method_from_id(req.did_claw)
        public_key = public_key_from_did_key(req.did_key)
        derived = did_claw_from_public_key(public_key, method=method)
        if derived != req.did_claw:
            raise ValueError("did_claw does not match did_key derivation")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    db = db_infra.manager()
    created_at = _now()
    updated_at = created_at

    async with db.transaction() as tx:
        existing = await tx.fetch_one(
            "SELECT did_claw FROM {{tables.did_claw_mappings}} WHERE did_claw = $1",
            req.did_claw,
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="did_claw already registered")

        state_hash = _state_hash(
            did_claw=req.did_claw,
            current_did_key=req.did_key,
            server=canonical_server,
            address=req.address,
            handle=req.handle,
        )
        if state_hash != req.state_hash:
            raise HTTPException(status_code=400, detail="state_hash mismatch")

        entry_payload = _log_entry_payload(
            did_claw=req.did_claw,
            seq=1,
            operation="create",
            previous_did_key=None,
            new_did_key=req.did_key,
            prev_entry_hash=None,
            state_hash=state_hash,
            authorized_by=req.did_key,
            timestamp=req.timestamp,
        )
        try:
            verify_did_key_signature(
                did_key=req.did_key, payload=entry_payload, signature_b64=req.proof
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="invalid proof") from e

        await tx.execute(
            """
            INSERT INTO {{tables.did_claw_mappings}}
                (did_claw, current_did_key, server_url, address, handle, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            req.did_claw,
            req.did_key,
            canonical_server,
            req.address,
            req.handle,
            created_at,
            updated_at,
        )

        entry_hash = _sha256_hex(entry_payload)

        await tx.execute(
            """
            INSERT INTO {{tables.did_claw_log}}
                (did_claw, seq, operation, previous_did_key, new_did_key,
                 prev_entry_hash, entry_hash, state_hash, authorized_by, signature,
                 timestamp, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            """,
            req.did_claw,
            1,
            "create",
            None,
            req.did_key,
            None,
            entry_hash,
            state_hash,
            req.did_key,
            req.proof,
            req.timestamp,
            created_at,
        )

    return {"registered": True}


@router.get(
    "/{did_claw}/key",
    response_model=DidKeyResponse,
    dependencies=[Depends(rate_limit_dep("did_key"))],
)
async def get_key(
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> DidKeyResponse:
    try:
        validate_stable_id(did_claw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db = db_infra.manager()
    row = await db.fetch_one(
        """
        SELECT did_claw, current_did_key
        FROM {{tables.did_claw_mappings}}
        WHERE did_claw = $1
        """,
        did_claw,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    head = await db.fetch_one(
        """
        SELECT seq, operation, previous_did_key, new_did_key,
               prev_entry_hash, entry_hash, state_hash, authorized_by, signature,
               timestamp
        FROM {{tables.did_claw_log}}
        WHERE did_claw = $1
        ORDER BY seq DESC
        LIMIT 1
        """,
        did_claw,
    )
    if head is None:
        raise HTTPException(status_code=500, detail="log missing for did_claw")
    if head["new_did_key"] != row["current_did_key"]:
        raise HTTPException(status_code=500, detail="mapping/log inconsistency")
    return DidKeyResponse(
        did_claw=row["did_claw"],
        current_did_key=row["current_did_key"],
        log_head=DidKeyEvidence(
            seq=head["seq"],
            operation=head["operation"],
            previous_did_key=head["previous_did_key"],
            new_did_key=head["new_did_key"],
            prev_entry_hash=head["prev_entry_hash"],
            entry_hash=head["entry_hash"],
            state_hash=head["state_hash"],
            authorized_by=head["authorized_by"],
            signature=head["signature"],
            timestamp=head["timestamp"],
        ),
    )


@router.get(
    "/{did_claw}/head",
    response_model=DidHeadResponse,
    dependencies=[Depends(rate_limit_dep("did_head"))],
)
async def get_head(
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> DidHeadResponse:
    """
    Lightweight endpoint to learn the latest audit-log head without downloading the full log.

    Intended for clients that want to poll for updates (seq/entry_hash) before fetching `/key` or `/log`.
    """
    try:
        validate_stable_id(did_claw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    db = db_infra.manager()
    row = await db.fetch_one(
        """
        SELECT did_claw, current_did_key, updated_at
        FROM {{tables.did_claw_mappings}}
        WHERE did_claw = $1
        """,
        did_claw,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="not found")

    head = await db.fetch_one(
        """
        SELECT seq, entry_hash, state_hash, timestamp, new_did_key
        FROM {{tables.did_claw_log}}
        WHERE did_claw = $1
        ORDER BY seq DESC
        LIMIT 1
        """,
        did_claw,
    )
    if head is None:
        raise HTTPException(status_code=500, detail="log missing for did_claw")
    if head["new_did_key"] != row["current_did_key"]:
        raise HTTPException(status_code=500, detail="mapping/log inconsistency")

    return DidHeadResponse(
        did_claw=row["did_claw"],
        current_did_key=row["current_did_key"],
        seq=head["seq"],
        entry_hash=head["entry_hash"],
        state_hash=head["state_hash"],
        timestamp=head["timestamp"],
        updated_at=row["updated_at"],
    )


def _parse_didkey_auth(authorization: str | None) -> tuple[str, str]:
    if not authorization:
        raise ValueError("missing Authorization")
    parts = authorization.split(" ")
    if len(parts) != 3 or parts[0] != "DIDKey":
        raise ValueError("Authorization must be: DIDKey <did:key> <signature>")
    return parts[1], parts[2]


@router.get(
    "/{did_claw}/full",
    response_model=DidFullResponse,
    dependencies=[Depends(rate_limit_dep("did_full"))],
)
async def get_full(
    request: Request,
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
    authorization: str | None = Header(default=None),
    x_clawdid_timestamp: str | None = Header(default=None, alias="X-ClawDID-Timestamp"),
) -> DidFullResponse:
    try:
        validate_stable_id(did_claw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        did_key, sig = _parse_didkey_auth(authorization)
        if not x_clawdid_timestamp:
            raise ValueError("missing X-ClawDID-Timestamp")
        _enforce_timestamp_skew(x_clawdid_timestamp)
        signing_payload = (
            f"{x_clawdid_timestamp}\n{request.method}\n{request.url.path}".encode(
                "utf-8"
            )
        )
        verify_did_key_signature(
            did_key=did_key, payload=signing_payload, signature_b64=sig
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    db = db_infra.manager()
    row = await db.fetch_one(
        """
        SELECT did_claw, current_did_key, server_url, address, handle, created_at, updated_at
        FROM {{tables.did_claw_mappings}}
        WHERE did_claw = $1
        """,
        did_claw,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        server_url = _require_canonical_server_origin(row["server_url"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return DidFullResponse(
        did_claw=row["did_claw"],
        current_did_key=row["current_did_key"],
        server=server_url,
        address=row["address"],
        handle=row["handle"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get(
    "/{did_claw}/log",
    response_model=list[DidLogEntry],
    dependencies=[Depends(rate_limit_dep("did_log"))],
)
async def get_log(
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> list[DidLogEntry]:
    try:
        validate_stable_id(did_claw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db = db_infra.manager()
    rows = await db.fetch_all(
        """
        SELECT did_claw, seq, operation, previous_did_key, new_did_key,
               prev_entry_hash, entry_hash, state_hash, authorized_by, signature,
               timestamp
        FROM {{tables.did_claw_log}}
        WHERE did_claw = $1
        ORDER BY seq ASC
        """,
        did_claw,
    )
    return [
        DidLogEntry(
            did_claw=r["did_claw"],
            seq=r["seq"],
            operation=r["operation"],
            previous_did_key=r["previous_did_key"],
            new_did_key=r["new_did_key"],
            prev_entry_hash=r["prev_entry_hash"],
            entry_hash=r["entry_hash"],
            state_hash=r["state_hash"],
            authorized_by=r["authorized_by"],
            signature=r["signature"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]


@router.put(
    "/{did_claw}",
    dependencies=[Depends(rate_limit_dep("did_update"))],
)
async def update_mapping(
    did_claw: str,
    req: DidUpdateRequest,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> dict:
    try:
        validate_stable_id(did_claw)
        _enforce_timestamp_skew(req.timestamp)
        # Ensure the new key is a syntactically valid did:key (Ed25519).
        public_key_from_did_key(req.new_did_key)
        if req.server is not None:
            _require_canonical_server_origin(req.server)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    db = db_infra.manager()
    async with db.transaction() as tx:
        row = await tx.fetch_one(
            """
            SELECT did_claw, current_did_key, server_url, address, handle
            FROM {{tables.did_claw_mappings}}
            WHERE did_claw = $1
            """,
            did_claw,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="not found")

        previous_did_key = row["current_did_key"]
        if req.authorized_by != previous_did_key:
            raise HTTPException(
                status_code=401, detail="authorized_by must be current did:key"
            )

        # Append log entry
        last = await tx.fetch_one(
            """
            SELECT seq, entry_hash
            FROM {{tables.did_claw_log}}
            WHERE did_claw = $1
            ORDER BY seq DESC
            LIMIT 1
            """,
            did_claw,
        )
        if last is None:
            raise HTTPException(status_code=500, detail="missing audit log head")
        next_seq = last["seq"] + 1
        prev_entry_hash = last["entry_hash"]
        if req.seq != next_seq:
            raise HTTPException(status_code=409, detail="seq mismatch")
        if req.prev_entry_hash != prev_entry_hash:
            raise HTTPException(status_code=409, detail="prev_entry_hash mismatch")

        try:
            server_url = _require_canonical_server_origin(
                req.server or row["server_url"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        address = req.address or row["address"]
        handle = req.handle if req.handle is not None else row["handle"]

        state_hash = _state_hash(
            did_claw=did_claw,
            current_did_key=req.new_did_key,
            server=server_url,
            address=address,
            handle=handle,
        )
        if state_hash != req.state_hash:
            raise HTTPException(status_code=400, detail="state_hash mismatch")

        entry_payload = _log_entry_payload(
            did_claw=did_claw,
            seq=next_seq,
            operation=req.operation,
            previous_did_key=previous_did_key,
            new_did_key=req.new_did_key,
            prev_entry_hash=prev_entry_hash,
            state_hash=state_hash,
            authorized_by=req.authorized_by,
            timestamp=req.timestamp,
        )
        entry_hash = _sha256_hex(entry_payload)
        try:
            verify_did_key_signature(
                did_key=req.authorized_by,
                payload=entry_payload,
                signature_b64=req.signature,
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="invalid signature") from e

        await tx.execute(
            """
            UPDATE {{tables.did_claw_mappings}}
            SET current_did_key = $2,
                server_url = $3,
                address = $4,
                handle = $5,
                updated_at = NOW()
            WHERE did_claw = $1
            """,
            did_claw,
            req.new_did_key,
            server_url,
            address,
            handle,
        )

        await tx.execute(
            """
            INSERT INTO {{tables.did_claw_log}}
                (did_claw, seq, operation, previous_did_key, new_did_key,
                 prev_entry_hash, entry_hash, state_hash, authorized_by, signature,
                 timestamp, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,NOW())
            """,
            did_claw,
            next_seq,
            req.operation,
            previous_did_key,
            req.new_did_key,
            prev_entry_hash,
            entry_hash,
            state_hash,
            req.authorized_by,
            req.signature,
            req.timestamp,
        )

    return {"updated": True}
