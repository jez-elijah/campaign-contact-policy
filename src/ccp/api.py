"""Small stateless API: ask the policy engine whether a contact is allowed."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from .models import Channel, Policy, Touch, load_policy
from .policy import evaluate

_path = os.environ.get("CCP_POLICY_PATH")
POLICY: Policy = load_policy(Path(_path) if _path else None)

app = FastAPI(title="Contact Policy API", version="1.0.0")


class CheckRequest(BaseModel):
    consent: dict[Channel, bool]
    last_complaint_day: int | None = None
    history: list[Touch] = []
    proposed: Touch


class CheckResponse(BaseModel):
    allowed: bool
    reason: str | None = None
    policy_version: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/policy")
def get_policy() -> Policy:
    return POLICY


@app.post("/check-contact", response_model=CheckResponse)
def check_contact(req: CheckRequest) -> CheckResponse:
    d = evaluate(
        POLICY,
        consent=req.consent,
        last_complaint_day=req.last_complaint_day,
        history=req.history,
        proposed=req.proposed,
    )
    return CheckResponse(allowed=d.allowed, reason=d.reason, policy_version=POLICY.version)
