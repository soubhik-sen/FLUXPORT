from __future__ import annotations

from pydantic import BaseModel, Field


class RequestIdentity(BaseModel):
    subject: str | None = None
    email: str | None = None
    auth_source: str = "anonymous"
    claims: dict = Field(default_factory=dict)
    user_id: int | None = None
    role_names: list[str] = Field(default_factory=list)
