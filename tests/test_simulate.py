import pandas as pd
import pytest

from ccp.kpi import overall_summary
from ccp.policy import in_quiet_hours
from ccp.simulate import run_simulation


@pytest.fixture(scope="module")
def runs(customers, campaigns, policy):
    return {m: run_simulation(customers, campaigns, policy, m, days=56, seed=11)
            for m in ("naive", "consent_only", "full_policy")}


def test_deterministic(customers, campaigns, policy):
    a = run_simulation(customers, campaigns, policy, "full_policy", days=28, seed=5)
    b = run_simulation(customers, campaigns, policy, "full_policy", days=28, seed=5)
    pd.testing.assert_frame_equal(a, b)


def test_rejects_unknown_mode(customers, campaigns, policy):
    with pytest.raises(ValueError):
        run_simulation(customers, campaigns, policy, "blast")


def test_naive_sends_every_attempt(runs):
    df = runs["naive"]
    assert (df["status"] == "sent").all()


def test_volume_ordering(runs):
    sent = {m: (df["status"] == "sent").sum() for m, df in runs.items()}
    assert sent["full_policy"] < sent["consent_only"] < sent["naive"]


def test_consent_only_never_contacts_without_original_consent(runs, customers):
    consent = {c.id: c.consent for c in customers}
    sent = runs["consent_only"].query("status == 'sent'")
    assert all(consent[r.customer_id][r.channel] for r in sent.itertuples())


def test_full_policy_respects_all_rules(runs, customers, policy):
    r = policy.rules
    consent = {c.id: c.consent for c in customers}
    sent = runs["full_policy"].query("status == 'sent'")

    # consent (opt-outs only ever remove consent, so original consent is a superset)
    assert all(consent[x.customer_id][x.channel] for x in sent.itertuples())
    # quiet hours
    assert not any(in_quiet_hours(h, r.quiet_hours.start, r.quiet_hours.end) for h in sent["hour"])

    for _, g in sent.groupby("customer_id"):
        days = sorted(g["day"])
        assert all(b - a >= r.min_gap_days for a, b in zip(days, days[1:]))
        for d in days:
            window = g[(g["day"] <= d) & (g["day"] > d - 7)]
            assert len(window) <= r.max_contacts_per_week_all_channels
            for ch, cap in r.channel_caps.items():
                assert (window["channel"] == ch).sum() <= cap.per_week
                month = g[(g["day"] <= d) & (g["day"] > d - 30) & (g["channel"] == ch)]
                assert len(month) <= cap.per_month


def test_complaint_cooldown_honoured(runs, policy):
    sent = runs["full_policy"].query("status == 'sent'")
    cooldown = policy.rules.complaint_cooldown_days
    complaints = sent[sent["complained"]]
    assert len(complaints) > 0, "test needs at least one complaint to be meaningful"
    for c in complaints.itertuples():
        later = sent[(sent["customer_id"] == c.customer_id) & (sent["day"] > c.day)
                     & (sent["day"] < c.day + cooldown)]
        assert later.empty


def test_suppressed_rows_have_reasons_and_no_outcomes(runs):
    sup = runs["full_policy"].query("status == 'suppressed'")
    assert sup["reason"].notna().all()
    assert not sup[["responded", "opted_out", "complained"]].any().any()


def test_policy_reduces_complaints_and_opt_outs_vs_naive(runs, customers):
    n = len(customers)
    naive = overall_summary(runs["naive"], n)
    full = overall_summary(runs["full_policy"], n)
    assert full["complaint_rate"] < naive["complaint_rate"]
    assert full["opt_out_rate"] < naive["opt_out_rate"]
