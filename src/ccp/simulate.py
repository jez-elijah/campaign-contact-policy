"""Day-by-day campaign simulation under three sending modes.

IMPORTANT: customer behaviour (response, opt-out, complaint) comes from the
assumed OutcomeModel below, not from real data. Results show how the policy
mechanics interact under those assumptions; they are not empirical findings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .models import Campaign, Customer, Policy, Touch
from .policy import evaluate, in_quiet_hours

MODES = ("naive", "consent_only", "full_policy")
PRIORITY = {"portfolio": 0, "usage": 1}
COLUMNS = [
    "day", "week", "customer_id", "campaign_id", "campaign_type", "channel", "hour",
    "status", "reason", "responded", "opted_out", "complained",
]


@dataclass(frozen=True)
class OutcomeModel:
    base_response: dict[str, float] = field(
        default_factory=lambda: {"portfolio": 0.06, "usage": 0.08}
    )
    fatigue_decay: float = 0.30          # response multiplier = exp(-decay * contacts in prior 7d)
    optout_base: float = 0.002
    optout_per_recent: float = 0.002     # added per contact in prior 7d
    complaint_base: float = 0.0003
    complaint_no_consent: float = 0.010  # contacted on a channel without consent
    complaint_quiet: float = 0.003       # contacted during quiet hours
    complaint_per_recent: float = 0.0005


def _active_campaigns(campaigns: list[Campaign], day: int) -> list[Campaign]:
    active = [
        c for c in campaigns
        if c.start_day <= day <= c.end_day and (day - c.start_day) % c.send_every_days == 0
    ]
    return sorted(active, key=lambda c: (PRIORITY[c.type], c.id))


def run_simulation(
    customers: list[Customer],
    campaigns: list[Campaign],
    policy: Policy,
    mode: str,
    days: int = 56,
    seed: int = 42,
    model: OutcomeModel | None = None,
) -> pd.DataFrame:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    model = model or OutcomeModel()
    rng = np.random.default_rng(seed)
    qh = policy.rules.quiet_hours

    consent = {c.id: dict(c.consent) for c in customers}
    last_complaint: dict[int, int | None] = {c.id: c.last_complaint_day for c in customers}
    history: dict[int, list[Touch]] = {c.id: [] for c in customers}
    rows: list[tuple] = []

    for day in range(days):
        for camp in _active_campaigns(campaigns, day):
            for cust in customers:
                if cust.segment not in camp.segments:
                    continue
                hour = int(rng.integers(6, 24))
                proposed = Touch(day=day, hour=hour, channel=camp.channel)
                has_consent = consent[cust.id].get(camp.channel, False)

                if mode == "naive":
                    allowed, reason = True, None
                elif mode == "consent_only":
                    allowed, reason = has_consent, (None if has_consent else "no_consent")
                else:
                    d = evaluate(
                        policy,
                        consent=consent[cust.id],
                        last_complaint_day=last_complaint[cust.id],
                        history=history[cust.id],
                        proposed=proposed,
                    )
                    allowed, reason = d.allowed, d.reason

                base = (day, day // 7, cust.id, camp.id, camp.type, camp.channel, hour)
                if not allowed:
                    rows.append(base + ("suppressed", reason, False, False, False))
                    continue

                recent = sum(1 for t in history[cust.id] if 0 <= day - t.day < 7)
                p_resp = min(
                    1.0,
                    model.base_response[camp.type] * cust.propensity
                    * math.exp(-model.fatigue_decay * recent),
                )
                p_opt = min(1.0, model.optout_base + model.optout_per_recent * recent)
                p_comp = model.complaint_base + model.complaint_per_recent * recent
                if not has_consent:
                    p_comp += model.complaint_no_consent
                if in_quiet_hours(hour, qh.start, qh.end):
                    p_comp += model.complaint_quiet

                u = rng.random(3)
                responded = bool(u[0] < p_resp)
                opted_out = bool(u[1] < p_opt)
                complained = bool(u[2] < p_comp)
                history[cust.id].append(proposed)
                if opted_out:
                    consent[cust.id][camp.channel] = False
                if complained:
                    last_complaint[cust.id] = day
                rows.append(base + ("sent", None, responded, opted_out, complained))

    return pd.DataFrame(rows, columns=COLUMNS)
