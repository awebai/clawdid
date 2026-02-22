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
    timestamp: str = Field(..., max_length=64)
    proof: str = Field(..., max_length=2048)


class DidKeyResponse(BaseModel):
    did_claw: str
    current_did_key: str


class DidFullResponse(BaseModel):
    did_claw: str
    current_did_key: str
    server: str
    address: str
    handle: Optional[str]
    created_at: datetime
    updated_at: datetime


class DidUpdateRequest(BaseModel):
    operation: Literal["rotate_key", "update_server", "update_address"] = "rotate_key"
    new_did_key: str = Field(..., max_length=256)
    server: Optional[str] = Field(default=None, max_length=512)
    address: Optional[str] = Field(default=None, max_length=256)
    handle: Optional[str] = Field(default=None, max_length=256)
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
