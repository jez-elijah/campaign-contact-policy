"""Seeded synthetic customer generator. No real customer data is used."""
from __future__ import annotations

import numpy as np

from .models import Customer

SEGMENTS = ("A", "B", "C")
CONSENT_RATE = {"sms": 0.70, "email": 0.85, "push": 0.60}


def generate_customers(n: int, seed: int = 42) -> list[Customer]:
    if n <= 0:
        raise ValueError("n must be positive")
    rng = np.random.default_rng(seed)
    segments = rng.choice(SEGMENTS, size=n, p=[0.3, 0.4, 0.3])
    propensity = rng.gamma(shape=2.0, scale=0.5, size=n)  # mean ~1.0
    customers = []
    for i in range(n):
        consent = {ch: bool(rng.random() < p) for ch, p in CONSENT_RATE.items()}
        customers.append(
            Customer(id=i, segment=str(segments[i]), consent=consent, propensity=float(propensity[i]))
        )
    return customers
