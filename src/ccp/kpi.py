"""KPI monitoring: weekly campaign KPIs and threshold alerts."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .models import Thresholds


def weekly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    sent = df[df["status"] == "sent"]
    g_all = df.groupby("week").size().rename("attempted")
    g_sent = sent.groupby("week").agg(
        sent=("status", "size"),
        responses=("responded", "sum"),
        opt_outs=("opted_out", "sum"),
        complaints=("complained", "sum"),
    )
    out = pd.concat([g_all, g_sent], axis=1).fillna(0).astype(int)
    out["suppressed"] = out["attempted"] - out["sent"]
    denom = out["sent"].where(out["sent"] > 0)
    out["response_rate"] = (out["responses"] / denom).fillna(0.0)
    out["opt_out_rate"] = (out["opt_outs"] / denom).fillna(0.0)
    out["complaint_rate"] = (out["complaints"] / denom).fillna(0.0)
    out["suppression_rate"] = (out["suppressed"] / out["attempted"].where(out["attempted"] > 0)).fillna(0.0)
    return out.reset_index()


def suppression_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    sup = df[df["status"] == "suppressed"]
    counts = sup["reason"].value_counts().rename_axis("reason").reset_index(name="count")
    counts["share"] = counts["count"] / max(len(sup), 1)
    return counts


@dataclass(frozen=True)
class Alert:
    week: int
    metric: str
    value: float
    threshold: float
    direction: str  # "above" or "below"


def check_alerts(kpis: pd.DataFrame, t: Thresholds) -> list[Alert]:
    checks = [
        ("opt_out_rate", t.max_opt_out_rate, "above"),
        ("complaint_rate", t.max_complaint_rate, "above"),
        ("suppression_rate", t.max_suppression_rate, "above"),
        ("response_rate", t.min_response_rate, "below"),
    ]
    alerts: list[Alert] = []
    for _, row in kpis.iterrows():
        for metric, limit, direction in checks:
            if metric == "response_rate" and row["sent"] == 0:
                continue  # nothing sent, nothing to judge
            value = float(row[metric])
            if (direction == "above" and value > limit) or (direction == "below" and value < limit):
                alerts.append(Alert(int(row["week"]), metric, value, limit, direction))
    return alerts


def overall_summary(df: pd.DataFrame, n_customers: int) -> dict[str, float]:
    sent = df[df["status"] == "sent"]
    n = len(sent)
    return {
        "attempted": len(df),
        "sent": n,
        "contacts_per_customer": n / n_customers,
        "responses": int(sent["responded"].sum()),
        "response_rate": float(sent["responded"].mean()) if n else 0.0,
        "opt_outs": int(sent["opted_out"].sum()),
        "opt_out_rate": float(sent["opted_out"].mean()) if n else 0.0,
        "complaints": int(sent["complained"].sum()),
        "complaint_rate": float(sent["complained"].mean()) if n else 0.0,
    }
