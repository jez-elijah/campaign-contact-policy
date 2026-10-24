"""Contact Policy engine: decides whether a proposed contact is allowed.

Rules are checked in a fixed order and the first failure is returned as the
reason code, so suppression reporting is unambiguous.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import Channel, Policy, Touch

REASONS = (
    "no_consent",
    "complaint_cooldown",
    "quiet_hours",
    "min_gap",
    "channel_week_cap",
    "channel_month_cap",
    "total_week_cap",
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str | None = None


def in_quiet_hours(hour: int, start: int, end: int) -> bool:
    """Quiet window may wrap midnight (e.g. 21 -> 8)."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def evaluate(
    policy: Policy,
    *,
    consent: dict[Channel, bool],
    last_complaint_day: int | None,
    history: Sequence[Touch],
    proposed: Touch,
) -> Decision:
    r = policy.rules
    day = proposed.day

    if r.require_consent and not consent.get(proposed.channel, False):
        return Decision(False, "no_consent")

    if last_complaint_day is not None and day - last_complaint_day < r.complaint_cooldown_days:
        return Decision(False, "complaint_cooldown")

    if in_quiet_hours(proposed.hour, r.quiet_hours.start, r.quiet_hours.end):
        return Decision(False, "quiet_hours")

    if any(day - t.day < r.min_gap_days for t in history if t.day <= day):
        return Decision(False, "min_gap")

    week = [t for t in history if 0 <= day - t.day < 7]
    month = [t for t in history if 0 <= day - t.day < 30]
    cap = r.channel_caps[proposed.channel]
    if sum(t.channel == proposed.channel for t in week) >= cap.per_week:
        return Decision(False, "channel_week_cap")
    if sum(t.channel == proposed.channel for t in month) >= cap.per_month:
        return Decision(False, "channel_month_cap")
    if len(week) >= r.max_contacts_per_week_all_channels:
        return Decision(False, "total_week_cap")

    return Decision(True)
