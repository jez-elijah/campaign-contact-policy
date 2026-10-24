from ccp.models import Touch
from ccp.policy import evaluate, in_quiet_hours

ALL = {"sms": True, "email": True, "push": True}


def check(policy, proposed, history=(), consent=ALL, last_complaint_day=None):
    return evaluate(
        policy, consent=consent, last_complaint_day=last_complaint_day,
        history=list(history), proposed=proposed,
    )


def t(day, hour=12, channel="sms"):
    return Touch(day=day, hour=hour, channel=channel)


def test_clean_contact_allowed(policy):
    d = check(policy, t(0))
    assert d.allowed and d.reason is None


def test_no_consent_suppressed(policy):
    d = check(policy, t(0), consent={"sms": False, "email": True, "push": True})
    assert (d.allowed, d.reason) == (False, "no_consent")


def test_missing_channel_in_consent_treated_as_no_consent(policy):
    assert check(policy, t(0), consent={}).reason == "no_consent"


def test_require_consent_can_be_disabled(policy):
    relaxed = policy.model_copy(deep=True)
    relaxed.rules.require_consent = False
    assert check(relaxed, t(0), consent={}).allowed


def test_complaint_cooldown_boundary(policy):
    assert check(policy, t(29), last_complaint_day=0).reason == "complaint_cooldown"
    assert check(policy, t(30), last_complaint_day=0).allowed


def test_quiet_hours_boundaries(policy):
    for hour in (21, 23, 0, 7):
        assert check(policy, t(0, hour)).reason == "quiet_hours", hour
    for hour in (8, 12, 20):
        assert check(policy, t(0, hour)).allowed, hour


def test_in_quiet_hours_non_wrapping_and_equal_window():
    assert in_quiet_hours(13, 12, 14)
    assert not in_quiet_hours(14, 12, 14)
    assert not in_quiet_hours(5, 6, 6)


def test_min_gap(policy):
    hist = [t(5, channel="push")]
    assert check(policy, t(6, channel="email"), hist).reason == "min_gap"
    assert check(policy, t(5, channel="email"), hist).reason == "min_gap"
    assert check(policy, t(7, channel="email"), hist).allowed


def test_channel_week_cap(policy):
    hist = [t(0)]  # sms cap is 1 per week
    assert check(policy, t(3), hist).reason == "channel_week_cap"
    assert check(policy, t(7), hist).allowed


def test_channel_month_cap(policy):
    hist = [t(0), t(7), t(14)]  # sms cap is 3 per 30 days
    assert check(policy, t(21), hist).reason == "channel_month_cap"
    assert check(policy, t(30), hist).allowed  # day 0 has aged out of the window


def test_total_week_cap(policy):
    hist = [t(0, channel="push"), t(2, channel="email"), t(4, channel="sms")]
    assert check(policy, t(6, channel="push"), hist).reason == "total_week_cap"


def test_rule_order_consent_before_quiet_hours(policy):
    d = check(policy, t(0, hour=23), consent={"sms": False, "email": True, "push": True})
    assert d.reason == "no_consent"
