import pytest

import pip
from pip._internal.download import PipSession
from pip._internal.network.requests import CI_ENVIRONMENT_VARIABLES


def get_user_agent():
    return PipSession().headers["User-Agent"]


def test_user_agent():
    user_agent = get_user_agent()

    assert user_agent.startswith("pip/%s" % pip.__version__)


@pytest.mark.parametrize('name, expected_like_ci', [
    ('BUILD_BUILDID', True),
    ('BUILD_ID', True),
    ('CI', True),
    ('PIP_IS_CI', True),
    # Test a prefix substring of one of the variable names we use.
    ('BUILD', False),
])
def test_user_agent__ci(monkeypatch, name, expected_like_ci):
    # Delete the variable names we use to check for CI to prevent the
    # detection from always returning True in case the tests are being run
    # under actual CI.  It is okay to depend on CI_ENVIRONMENT_VARIABLES
    # here (part of the code under test) because this setup step can only
    # prevent false test failures.  It can't cause a false test passage.
    for ci_name in CI_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(ci_name, raising=False)

    # Confirm the baseline before setting the environment variable.
    user_agent = get_user_agent()
    assert '"ci":null' in user_agent
    assert '"ci":true' not in user_agent

    monkeypatch.setenv(name, 'true')
    user_agent = get_user_agent()
    assert ('"ci":true' in user_agent) == expected_like_ci
    assert ('"ci":null' in user_agent) == (not expected_like_ci)


def test_user_agent_user_data(monkeypatch):
    monkeypatch.setenv("PIP_USER_AGENT_USER_DATA", "some_string")
    assert "some_string" in PipSession().headers["User-Agent"]
