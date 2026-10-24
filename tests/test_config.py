import pytest
from pydantic import ValidationError

from ccp.models import Policy


def test_default_config_loads(policy, campaigns):
    assert policy.version == 1
    assert len(campaigns) == len({c.id for c in campaigns})


def test_campaigns_use_known_channels_and_caps(policy, campaigns):
    assert all(c.channel in policy.rules.channel_caps for c in campaigns)


def test_invalid_policy_rejected():
    with pytest.raises(ValidationError):
        Policy.model_validate({"version": 1, "rules": {}, "monitoring": {}})
