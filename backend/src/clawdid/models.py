from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DidRegisterRequest(BaseModel):
    did_claw: str = Field(..., max_length=256)
    did_key: str = Field(..., max_length=256)
    server: str = Field(..., max_length=512)
    address: str = Field(..., max_length=256)
    handle: Optional[str] = Field(default=None, max_length=256)
    # Log entry binding: make the audit trail self-verifying.
    seq: int = Field(default=1, ge=1)
    prev_entry_hash: Optional[str] = Field(default=None, max_length=128)
    state_hash: str = Field(..., max_length=128)
    authorized_by: str = Field(..., max_length=256)
    timestamp: str = Field(..., max_length=64)
    proof: str = Field(..., max_length=2048)


class DidKeyEvidence(BaseModel):
    seq: int
    operation: str
    previous_did_key: Optional[str]
    new_did_key: str
    prev_entry_hash: Optional[str]
    entry_hash: str
    state_hash: str
    authorized_by: str
    signature: str
    timestamp: str


class DidKeyResponse(BaseModel):
    did_claw: str
    current_did_key: str
    log_head: Optional[DidKeyEvidence] = None


class DidHeadResponse(BaseModel):
    did_claw: str
    current_did_key: str
    seq: int
    entry_hash: str
    state_hash: str
    timestamp: str
    updated_at: datetime


class DidFullResponse(BaseModel):
    did_claw: str
    current_did_key: str
    server: str
    address: str
    handle: Optional[str]
    created_at: datetime
    updated_at: datetime


class DidUpdateRequest(BaseModel):
    operation: Literal["rotate_key", "update_server"] = "rotate_key"
    new_did_key: str = Field(..., max_length=256)
    server: Optional[str] = Field(default=None, max_length=512)
    seq: int = Field(..., ge=1)
    prev_entry_hash: str = Field(..., max_length=128)
    state_hash: str = Field(..., max_length=128)
    authorized_by: str = Field(..., max_length=256)
    timestamp: str = Field(..., max_length=64)
    signature: str = Field(..., max_length=2048)


class DidLogEntry(BaseModel):
    did_claw: str
    seq: int
    operation: str
    previous_did_key: Optional[str]
    new_did_key: str
    prev_entry_hash: Optional[str]
    entry_hash: str
    state_hash: str
    authorized_by: str
    signature: str
    timestamp: str
