"""Run all three modes and write KPI reports.  Usage: python -m ccp.cli --customers 5000"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .generate import generate_customers
from .kpi import check_alerts, overall_summary, suppression_breakdown, weekly_kpis
from .models import load_campaigns, load_policy
from .simulate import MODES, run_simulation


def main(argv: list[str] | None = None) -> pd.DataFrame:
    ap = argparse.ArgumentParser()
    ap.add_argument("--customers", type=int, default=5000)
    ap.add_argument("--days", type=int, default=56)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("outputs"))
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    policy, campaigns = load_policy(), load_campaigns()
    customers = generate_customers(args.customers, args.seed)

    summary = {}
    for mode in MODES:
        df = run_simulation(customers, campaigns, policy, mode, args.days, args.seed)
        kpis = weekly_kpis(df)
        kpis.to_csv(args.out / f"weekly_kpis_{mode}.csv", index=False)
        suppression_breakdown(df).to_csv(args.out / f"suppressions_{mode}.csv", index=False)
        alerts = check_alerts(kpis, policy.monitoring)
        pd.DataFrame([a.__dict__ for a in alerts]).to_csv(args.out / f"alerts_{mode}.csv", index=False)
        s = overall_summary(df, len(customers))
        s["alerts"] = len(alerts)
        summary[mode] = s

    table = pd.DataFrame(summary).T
    table.to_csv(args.out / "summary.csv")
    with open(args.out / "summary.md", "w") as f:
        f.write(table.to_markdown(floatfmt=".4f") if _has_tabulate() else table.to_string())
    print(table.to_string(float_format=lambda x: f"{x:.4f}"))
    return table


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
