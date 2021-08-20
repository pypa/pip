import logging

import pytest

from pip import __version__
from pip._internal.network.session import CI_ENVIRONMENT_VARIABLES, PipSession


def get_user_agent():
    return PipSession().headers["User-Agent"]


def test_user_agent():
    user_agent = get_user_agent()

    assert user_agent.startswith(f"pip/{__version__}")


@pytest.mark.parametrize(
    "name, expected_like_ci",
    [
        ("BUILD_BUILDID", True),
        ("BUILD_ID", True),
        ("CI", True),
        ("PIP_IS_CI", True),
        # Test a prefix substring of one of the variable names we use.
        ("BUILD", False),
    ],
)
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

    monkeypatch.setenv(name, "true")
    user_agent = get_user_agent()
    assert ('"ci":true' in user_agent) == expected_like_ci
    assert ('"ci":null' in user_agent) == (not expected_like_ci)


def test_user_agent_user_data(monkeypatch):
    monkeypatch.setenv("PIP_USER_AGENT_USER_DATA", "some_string")
    assert "some_string" in PipSession().headers["User-Agent"]


class TestPipSession:
    def test_cache_defaults_off(self):
        session = PipSession()

        assert not hasattr(session.adapters["http://"], "cache")
        assert not hasattr(session.adapters["https://"], "cache")

    def test_cache_is_enabled(self, tmpdir):
        cache_directory = tmpdir.joinpath("test-cache")
        session = PipSession(cache=cache_directory)

        assert hasattr(session.adapters["https://"], "cache")

        assert session.adapters["https://"].cache.directory == cache_directory

    def test_http_cache_is_not_enabled(self, tmpdir):
        session = PipSession(cache=tmpdir.joinpath("test-cache"))

        assert not hasattr(session.adapters["http://"], "cache")

    def test_trusted_hosts_adapter(self, tmpdir):
        session = PipSession(
            cache=tmpdir.joinpath("test-cache"),
            trusted_hosts=["example.com"],
        )

        assert "https://example.com/" in session.adapters
        # Check that the "port wildcard" is present.
        assert "https://example.com:" in session.adapters
        # Check that the cache is enabled.
        assert hasattr(session.adapters["https://example.com/"], "cache")

    def test_add_trusted_host(self):
        # Leave a gap to test how the ordering is affected.
        trusted_hosts = ["host1", "host3"]
        session = PipSession(trusted_hosts=trusted_hosts)
        trusted_host_adapter = session._trusted_host_adapter
        prefix2 = "https://host2/"
        prefix3 = "https://host3/"
        prefix3_wildcard = "https://host3:"

        # Confirm some initial conditions as a baseline.
        assert session.pip_trusted_origins == [("host1", None), ("host3", None)]
        assert session.adapters[prefix3] is trusted_host_adapter
        assert session.adapters[prefix3_wildcard] is trusted_host_adapter

        assert prefix2 not in session.adapters

        # Test adding a new host.
        session.add_trusted_host("host2")
        assert session.pip_trusted_origins == [
            ("host1", None),
            ("host3", None),
            ("host2", None),
        ]
        # Check that prefix3 is still present.
        assert session.adapters[prefix3] is trusted_host_adapter
        assert session.adapters[prefix2] is trusted_host_adapter

        # Test that adding the same host doesn't create a duplicate.
        session.add_trusted_host("host3")
        assert session.pip_trusted_origins == [
            ("host1", None),
            ("host3", None),
            ("host2", None),
        ], f"actual: {session.pip_trusted_origins}"

        session.add_trusted_host("host4:8080")
        prefix4 = "https://host4:8080/"
        assert session.pip_trusted_origins == [
            ("host1", None),
            ("host3", None),
            ("host2", None),
            ("host4", 8080),
        ]
        assert session.adapters[prefix4] is trusted_host_adapter

    def test_add_trusted_host__logging(self, caplog):
        """
        Test logging when add_trusted_host() is called.
        """
        trusted_hosts = ["host0", "host1"]
        session = PipSession(trusted_hosts=trusted_hosts)
        with caplog.at_level(logging.INFO):
            # Test adding an existing host.
            session.add_trusted_host("host1", source="somewhere")
            session.add_trusted_host("host2")
            # Test calling add_trusted_host() on the same host twice.
            session.add_trusted_host("host2")

        actual = [(r.levelname, r.message) for r in caplog.records]
        # Observe that "host0" isn't included in the logs.
        expected = [
            ("INFO", "adding trusted host: 'host1' (from somewhere)"),
            ("INFO", "adding trusted host: 'host2'"),
            ("INFO", "adding trusted host: 'host2'"),
        ]
        assert actual == expected

    def test_iter_secure_origins(self):
        trusted_hosts = ["host1", "host2", "host3:8080"]
        session = PipSession(trusted_hosts=trusted_hosts)

        actual = list(session.iter_secure_origins())
        assert len(actual) == 9
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ("https", "*", "*")
        assert actual[-3:] == [
            ("*", "host1", "*"),
            ("*", "host2", "*"),
            ("*", "host3", 8080),
        ]

    def test_iter_secure_origins__trusted_hosts_empty(self):
        """
        Test iter_secure_origins() after passing trusted_hosts=[].
        """
        session = PipSession(trusted_hosts=[])

        actual = list(session.iter_secure_origins())
        assert len(actual) == 6
        # Spot-check that SECURE_ORIGINS is included.
        assert actual[0] == ("https", "*", "*")

    @pytest.mark.parametrize(
        "location, trusted, expected",
        [
            ("http://pypi.org/something", [], False),
            ("https://pypi.org/something", [], True),
            ("git+http://pypi.org/something", [], False),
            ("git+https://pypi.org/something", [], True),
            ("git+ssh://git@pypi.org/something", [], True),
            ("http://localhost", [], True),
            ("http://127.0.0.1", [], True),
            ("http://example.com/something/", [], False),
            ("http://example.com/something/", ["example.com"], True),
            # Try changing the case.
            ("http://eXample.com/something/", ["example.cOm"], True),
            # Test hosts with port.
            ("http://example.com:8080/something/", ["example.com"], True),
            # Test a trusted_host with a port.
            ("http://example.com:8080/something/", ["example.com:8080"], True),
            ("http://example.com/something/", ["example.com:8080"], False),
            ("http://example.com:8888/something/", ["example.com:8080"], False),
        ],
    )
    def test_is_secure_origin(self, caplog, location, trusted, expected):
        class MockLogger:
            def __init__(self):
                self.called = False

            def warning(self, *args, **kwargs):
                self.called = True

        session = PipSession(trusted_hosts=trusted)
        actual = session.is_secure_origin(location)
        assert actual == expected

        log_records = [(r.levelname, r.message) for r in caplog.records]
        if expected:
            assert not log_records
            return

        assert len(log_records) == 1
        actual_level, actual_message = log_records[0]
        assert actual_level == "WARNING"
        assert "is not a trusted or secure host" in actual_message
