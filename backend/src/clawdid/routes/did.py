from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from clawdid.config import settings
from clawdid.db import DatabaseInfra, get_db_infra
from clawdid.did import (did_claw_from_public_key, public_key_from_did_key,
                         validate_stable_id)
from clawdid.models import (DidFullResponse, DidKeyResponse, DidLogEntry,
                            DidRegisterRequest, DidUpdateRequest)
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
    return dt.astimezone(timezone.utc)


def _enforce_timestamp_skew(ts: str) -> None:
    dt = _parse_rfc3339(ts)
    delta = abs((_now() - dt).total_seconds())
    if delta > settings.auth_timestamp_skew_seconds:
        raise ValueError("timestamp outside allowed skew window")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


@router.post("")
async def register_did(
    req: DidRegisterRequest,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> dict:
    try:
        validate_stable_id(req.did_claw)
        _enforce_timestamp_skew(req.timestamp)
        derived = did_claw_from_public_key(
            public_key_from_did_key(req.did_key),
            method=settings.clawdid_method,
        )
        if derived != req.did_claw:
            raise ValueError("did_claw does not match did_key derivation")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    proof_payload = canonical_json_bytes(
        {
            "action": "register",
            "address": req.address,
            "did_claw": req.did_claw,
            "did_key": req.did_key,
            "handle": req.handle,
            "server": req.server,
            "timestamp": req.timestamp,
        }
    )
    try:
        verify_did_key_signature(
            did_key=req.did_key, payload=proof_payload, signature_b64=req.proof
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="invalid proof") from e

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
            server=req.server,
            address=req.address,
            handle=req.handle,
        )

        await tx.execute(
            """
            INSERT INTO {{tables.did_claw_mappings}}
                (did_claw, current_did_key, server_url, address, handle, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            req.did_claw,
            req.did_key,
            req.server,
            req.address,
            req.handle,
            created_at,
            updated_at,
        )

        prev_entry_hash = None
        entry_payload = canonical_json_bytes(
            {
                "address": req.address,
                "authorized_by": req.did_key,
                "did_claw": req.did_claw,
                "new_did_key": req.did_key,
                "operation": "create",
                "prev_entry_hash": prev_entry_hash,
                "previous_did_key": None,
                "seq": 1,
                "server": req.server,
                "state_hash": state_hash,
                "timestamp": req.timestamp,
            }
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
            prev_entry_hash,
            entry_hash,
            state_hash,
            req.did_key,
            req.proof,
            req.timestamp,
            created_at,
        )

    return {"registered": True}


@router.get("/{did_claw}/key", response_model=DidKeyResponse)
async def get_key(
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> DidKeyResponse:
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
    return DidKeyResponse(
        did_claw=row["did_claw"], current_did_key=row["current_did_key"]
    )


def _parse_didkey_auth(authorization: str | None) -> tuple[str, str]:
    if not authorization:
        raise ValueError("missing Authorization")
    parts = authorization.split(" ")
    if len(parts) != 3 or parts[0] != "DIDKey":
        raise ValueError("Authorization must be: DIDKey <did:key> <signature>")
    return parts[1], parts[2]


@router.get("/{did_claw}/full", response_model=DidFullResponse)
async def get_full(
    request: Request,
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
    authorization: str | None = Header(default=None),
    x_clawdid_timestamp: str | None = Header(default=None, alias="X-Clawdid-Timestamp"),
) -> DidFullResponse:
    try:
        did_key, sig = _parse_didkey_auth(authorization)
        if not x_clawdid_timestamp:
            raise ValueError("missing X-Clawdid-Timestamp")
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
    return DidFullResponse(
        did_claw=row["did_claw"],
        current_did_key=row["current_did_key"],
        server=row["server_url"],
        address=row["address"],
        handle=row["handle"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/{did_claw}/log", response_model=list[DidLogEntry])
async def get_log(
    did_claw: str,
    db_infra: DatabaseInfra = Depends(get_db_infra),
) -> list[DidLogEntry]:
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


@router.put("/{did_claw}")
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

        update_payload = canonical_json_bytes(
            {
                "action": "update",
                "address": req.address or row["address"],
                "did_claw": did_claw,
                "new_did_key": req.new_did_key,
                "operation": req.operation,
                "previous_did_key": previous_did_key,
                "server": req.server or row["server_url"],
                "timestamp": req.timestamp,
            }
        )
        try:
            verify_did_key_signature(
                did_key=req.authorized_by,
                payload=update_payload,
                signature_b64=req.signature,
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail="invalid signature") from e

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
        next_seq = (last["seq"] if last else 0) + 1
        prev_entry_hash = last["entry_hash"] if last else None

        server_url = req.server or row["server_url"]
        address = req.address or row["address"]
        handle = req.handle if req.handle is not None else row["handle"]

        state_hash = _state_hash(
            did_claw=did_claw,
            current_did_key=req.new_did_key,
            server=server_url,
            address=address,
            handle=handle,
        )

        entry_payload = canonical_json_bytes(
            {
                "address": address,
                "authorized_by": req.authorized_by,
                "did_claw": did_claw,
                "new_did_key": req.new_did_key,
                "operation": req.operation,
                "prev_entry_hash": prev_entry_hash,
                "previous_did_key": previous_did_key,
                "seq": next_seq,
                "server": server_url,
                "state_hash": state_hash,
                "timestamp": req.timestamp,
            }
        )
        entry_hash = _sha256_hex(entry_payload)

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
