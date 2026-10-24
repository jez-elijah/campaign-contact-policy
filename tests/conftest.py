import pytest

from ccp.generate import generate_customers
from ccp.models import load_campaigns, load_policy


@pytest.fixture(scope="session")
def policy():
    return load_policy()


@pytest.fixture(scope="session")
def campaigns():
    return load_campaigns()


@pytest.fixture(scope="session")
def customers():
    return generate_customers(300, seed=7)
