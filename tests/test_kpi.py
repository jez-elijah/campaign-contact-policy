import pandas as pd

from ccp.kpi import check_alerts, overall_summary, suppression_breakdown, weekly_kpis
from ccp.models import Thresholds

COLS = ["week", "status", "reason", "responded", "opted_out", "complained"]


def frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_weekly_kpis_values():
    df = frame([
        (0, "sent", None, True, False, False),
        (0, "sent", None, False, True, False),
        (0, "sent", None, False, False, True),
        (0, "sent", None, False, False, False),
        (0, "suppressed", "min_gap", False, False, False),
    ])
    row = weekly_kpis(df).iloc[0]
    assert (row["attempted"], row["sent"], row["suppressed"]) == (5, 4, 1)
    assert row["response_rate"] == 0.25
    assert row["opt_out_rate"] == 0.25
    assert row["complaint_rate"] == 0.25
    assert row["suppression_rate"] == 0.2


def test_week_with_only_suppressed_has_zero_rates_not_nan():
    df = frame([(1, "suppressed", "no_consent", False, False, False)] * 3)
    row = weekly_kpis(df).iloc[0]
    assert row["sent"] == 0 and row["response_rate"] == 0.0 and row["suppression_rate"] == 1.0


def test_alerts_fire_in_both_directions_and_skip_empty_weeks():
    t = Thresholds(max_opt_out_rate=0.1, max_complaint_rate=0.1,
                   min_response_rate=0.5, max_suppression_rate=0.9)
    kpis = pd.DataFrame([
        dict(week=0, sent=10, response_rate=0.2, opt_out_rate=0.3, complaint_rate=0.0, suppression_rate=0.0),
        dict(week=1, sent=0, response_rate=0.0, opt_out_rate=0.0, complaint_rate=0.0, suppression_rate=1.0),
    ])
    got = {(a.week, a.metric, a.direction) for a in check_alerts(kpis, t)}
    assert got == {(0, "opt_out_rate", "above"), (0, "response_rate", "below"),
                   (1, "suppression_rate", "above")}


def test_no_alerts_when_within_thresholds():
    t = Thresholds(max_opt_out_rate=0.5, max_complaint_rate=0.5,
                   min_response_rate=0.0, max_suppression_rate=1.0)
    kpis = pd.DataFrame([dict(week=0, sent=5, response_rate=0.1, opt_out_rate=0.1,
                              complaint_rate=0.1, suppression_rate=0.5)])
    assert check_alerts(kpis, t) == []


def test_suppression_breakdown_shares_sum_to_one():
    df = frame([(0, "suppressed", "min_gap", False, False, False)] * 3
               + [(0, "suppressed", "no_consent", False, False, False)]
               + [(0, "sent", None, True, False, False)])
    b = suppression_breakdown(df)
    assert b.loc[b["reason"] == "min_gap", "count"].item() == 3
    assert abs(b["share"].sum() - 1.0) < 1e-12


def test_overall_summary():
    df = frame([(0, "sent", None, True, False, False), (0, "suppressed", "x", False, False, False)])
    s = overall_summary(df, n_customers=2)
    assert s["sent"] == 1 and s["contacts_per_customer"] == 0.5 and s["response_rate"] == 1.0
