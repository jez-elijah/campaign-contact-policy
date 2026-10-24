from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

Channel = Literal["sms", "email", "push"]
CampaignType = Literal["portfolio", "usage"]
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Customer(BaseModel):
    id: int
    segment: str
    consent: dict[Channel, bool]
    propensity: float = Field(ge=0)
    last_complaint_day: int | None = None


class Touch(BaseModel):
    """A contact that was (or would be) made."""

    day: int = Field(ge=0)
    hour: int = Field(ge=0, le=23)
    channel: Channel


class Campaign(BaseModel):
    id: str
    type: CampaignType
    channel: Channel
    start_day: int = Field(ge=0)
    end_day: int = Field(ge=0)
    send_every_days: int = Field(ge=1)
    segments: list[str]


class ChannelCap(BaseModel):
    per_week: int = Field(ge=0)
    per_month: int = Field(ge=0)


class QuietHours(BaseModel):
    start: int = Field(ge=0, le=23)
    end: int = Field(ge=0, le=23)


class Rules(BaseModel):
    require_consent: bool
    complaint_cooldown_days: int = Field(ge=0)
    quiet_hours: QuietHours
    min_gap_days: int = Field(ge=0)
    channel_caps: dict[Channel, ChannelCap]
    max_contacts_per_week_all_channels: int = Field(ge=0)


class Thresholds(BaseModel):
    max_opt_out_rate: float
    max_complaint_rate: float
    min_response_rate: float
    max_suppression_rate: float


class Policy(BaseModel):
    version: int
    rules: Rules
    monitoring: Thresholds


def load_policy(path: Path | None = None) -> Policy:
    path = path or CONFIG_DIR / "policy.yaml"
    return Policy.model_validate(yaml.safe_load(path.read_text()))


def load_campaigns(path: Path | None = None) -> list[Campaign]:
    path = path or CONFIG_DIR / "campaigns.yaml"
    raw = yaml.safe_load(path.read_text())["campaigns"]
    return [Campaign.model_validate(c) for c in raw]
