import pytest

from ccp.generate import CONSENT_RATE, SEGMENTS, generate_customers


def test_deterministic():
    assert generate_customers(50, seed=1) == generate_customers(50, seed=1)


def test_different_seed_differs():
    assert generate_customers(50, seed=1) != generate_customers(50, seed=2)


def test_valid_fields():
    cs = generate_customers(200, seed=3)
    assert len({c.id for c in cs}) == 200
    assert all(c.segment in SEGMENTS and c.propensity >= 0 for c in cs)


def test_consent_rates_close_to_targets():
    cs = generate_customers(5000, seed=4)
    for ch, target in CONSENT_RATE.items():
        rate = sum(c.consent[ch] for c in cs) / len(cs)
        assert abs(rate - target) < 0.03


def test_rejects_non_positive_n():
    with pytest.raises(ValueError):
        generate_customers(0)
