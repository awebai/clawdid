from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ReleaseIdentity:
    git_sha: str
    release_tag: str
    built_at: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def release_identity() -> ReleaseIdentity:
    return ReleaseIdentity(
        git_sha=os.environ.get("CLAWDID_GIT_SHA", ""),
        release_tag=os.environ.get("CLAWDID_RELEASE_TAG", ""),
        built_at=os.environ.get("CLAWDID_BUILT_AT", ""),
    )
