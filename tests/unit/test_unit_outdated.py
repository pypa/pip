import datetime
import json
import os
import sys

import freezegun
import pretend
import pytest
from mock import patch
from pip._vendor import pkg_resources

from pip._internal.index import InstallationCandidate
from pip._internal.network.session import PipSession
from pip._internal.utils import outdated
from pip._internal.utils.outdated import (
    SelfCheckState,
    logger,
    make_link_collector,
    pip_version_check,
)
from tests.lib.path import Path


@pytest.mark.parametrize(
    'find_links, no_index, suppress_no_index, expected', [
        (['link1'], False, False,
         (['link1'], ['default_url', 'url1', 'url2'])),
        (['link1'], False, True, (['link1'], ['default_url', 'url1', 'url2'])),
        (['link1'], True, False, (['link1'], [])),
        # Passing suppress_no_index=True suppresses no_index=True.
        (['link1'], True, True, (['link1'], ['default_url', 'url1', 'url2'])),
        # Test options.find_links=False.
        (False, False, False, ([], ['default_url', 'url1', 'url2'])),
    ],
)
def test_make_link_collector(
    find_links, no_index, suppress_no_index, expected,
):
    """
    :param expected: the expected (find_links, index_urls) values.
    """
    expected_find_links, expected_index_urls = expected
    session = PipSession()
    options = pretend.stub(
        find_links=find_links,
        index_url='default_url',
        extra_index_urls=['url1', 'url2'],
        no_index=no_index,
    )
    link_collector = make_link_collector(
        session, options=options, suppress_no_index=suppress_no_index,
    )

    assert link_collector.session is session

    search_scope = link_collector.search_scope
    assert search_scope.find_links == expected_find_links
    assert search_scope.index_urls == expected_index_urls


@patch('pip._internal.utils.misc.expanduser')
def test_make_link_collector__find_links_expansion(mock_expanduser, tmpdir):
    """
    Test "~" expansion in --find-links paths.
    """
    # This is a mock version of expanduser() that expands "~" to the tmpdir.
    def expand_path(path):
        if path.startswith('~/'):
            path = os.path.join(tmpdir, path[2:])
        return path

    mock_expanduser.side_effect = expand_path

    session = PipSession()
    options = pretend.stub(
        find_links=['~/temp1', '~/temp2'],
        index_url='default_url',
        extra_index_urls=[],
        no_index=False,
    )
    # Only create temp2 and not temp1 to test that "~" expansion only occurs
    # when the directory exists.
    temp2_dir = os.path.join(tmpdir, 'temp2')
    os.mkdir(temp2_dir)

    link_collector = make_link_collector(session, options=options)

    search_scope = link_collector.search_scope
    # Only ~/temp2 gets expanded. Also, the path is normalized when expanded.
    expected_temp2_dir = os.path.normcase(temp2_dir)
    assert search_scope.find_links == ['~/temp1', expected_temp2_dir]
    assert search_scope.index_urls == ['default_url']


class MockBestCandidateResult(object):
    def __init__(self, best):
        self.best_candidate = best


class MockPackageFinder(object):

    BASE_URL = 'https://pypi.org/simple/pip-{0}.tar.gz'
    PIP_PROJECT_NAME = 'pip'
    INSTALLATION_CANDIDATES = [
        InstallationCandidate(PIP_PROJECT_NAME, '6.9.0',
                              BASE_URL.format('6.9.0')),
        InstallationCandidate(PIP_PROJECT_NAME, '3.3.1',
                              BASE_URL.format('3.3.1')),
        InstallationCandidate(PIP_PROJECT_NAME, '1.0',
                              BASE_URL.format('1.0')),
    ]

    @classmethod
    def create(cls, *args, **kwargs):
        return cls()

    def find_best_candidate(self, project_name):
        return MockBestCandidateResult(self.INSTALLATION_CANDIDATES[0])


class MockDistribution(object):
    def __init__(self, installer):
        self.installer = installer

    def has_metadata(self, name):
        return name == 'INSTALLER'

    def get_metadata_lines(self, name):
        if self.has_metadata(name):
            yield self.installer
        else:
            raise NotImplementedError('nope')


def _options():
    ''' Some default options that we pass to outdated.pip_version_check '''
    return pretend.stub(
        find_links=[], index_url='default_url', extra_index_urls=[],
        no_index=False, pre=False, cache_dir='',
    )


@pytest.mark.parametrize(
    [
        'stored_time',
        'installed_ver',
        'new_ver',
        'installer',
        'check_if_upgrade_required',
        'check_warn_logs',
    ],
    [
        # Test we return None when installed version is None
        ('1970-01-01T10:00:00Z', None, '1.0', 'pip', False, False),
        # Need an upgrade - upgrade warning should print
        ('1970-01-01T10:00:00Z', '1.0', '6.9.0', 'pip', True, True),
        # Upgrade available, pip installed via rpm - warning should not print
        ('1970-01-01T10:00:00Z', '1.0', '6.9.0', 'rpm', True, False),
        # No upgrade - upgrade warning should not print
        ('1970-01-9T10:00:00Z', '6.9.0', '6.9.0', 'pip', False, False),
    ]
)
def test_pip_version_check(monkeypatch, stored_time, installed_ver, new_ver,
                           installer, check_if_upgrade_required,
                           check_warn_logs):
    monkeypatch.setattr(outdated, 'get_installed_version',
                        lambda name: installed_ver)
    monkeypatch.setattr(outdated, 'PackageFinder', MockPackageFinder)
    monkeypatch.setattr(logger, 'warning',
                        pretend.call_recorder(lambda *a, **kw: None))
    monkeypatch.setattr(logger, 'debug',
                        pretend.call_recorder(lambda s, exc_info=None: None))
    monkeypatch.setattr(pkg_resources, 'get_distribution',
                        lambda name: MockDistribution(installer))

    fake_state = pretend.stub(
        state={"last_check": stored_time, 'pypi_version': installed_ver},
        save=pretend.call_recorder(lambda v, t: None),
    )
    monkeypatch.setattr(
        outdated, 'SelfCheckState', lambda **kw: fake_state
    )

    with freezegun.freeze_time(
        "1970-01-09 10:00:00",
        ignore=[
            "six.moves",
            "pip._vendor.six.moves",
            "pip._vendor.requests.packages.urllib3.packages.six.moves",
        ]
    ):
        latest_pypi_version = pip_version_check(None, _options())

    # See we return None if not installed_version
    if not installed_ver:
        assert not latest_pypi_version
    # See that we saved the correct version
    elif check_if_upgrade_required:
        assert fake_state.save.calls == [
            pretend.call(new_ver, datetime.datetime(1970, 1, 9, 10, 00, 00)),
        ]
    else:
        # Make sure no Exceptions
        assert not logger.debug.calls
        # See that save was not called
        assert fake_state.save.calls == []

    # Ensure we warn the user or not
    if check_warn_logs:
        assert len(logger.warning.calls) == 1
    else:
        assert len(logger.warning.calls) == 0


statefile_name_case_1 = (
    "fcd2d5175dd33d5df759ee7b045264230205ef837bf9f582f7c3ada7"
)

statefile_name_case_2 = (
    "902cecc0745b8ecf2509ba473f3556f0ba222fedc6df433acda24aa5"
)


@pytest.mark.parametrize("key,expected", [
    ("/hello/world/venv", statefile_name_case_1),
    ("C:\\Users\\User\\Desktop\\venv", statefile_name_case_2),
])
def test_get_statefile_name_known_values(key, expected):
    assert expected == outdated._get_statefile_name(key)


def _get_statefile_path(cache_dir, key):
    return os.path.join(
        cache_dir, "selfcheck", outdated._get_statefile_name(key)
    )


def test_self_check_state_no_cache_dir():
    state = SelfCheckState(cache_dir=False)
    assert state.state == {}
    assert state.statefile_path is None


def test_self_check_state_key_uses_sys_prefix(monkeypatch):
    key = "helloworld"

    monkeypatch.setattr(sys, "prefix", key)
    state = outdated.SelfCheckState("")

    assert state.key == key


def test_self_check_state_reads_expected_statefile(monkeypatch, tmpdir):
    cache_dir = tmpdir / "cache_dir"
    cache_dir.mkdir()
    key = "helloworld"
    statefile_path = _get_statefile_path(str(cache_dir), key)

    last_check = "1970-01-02T11:00:00Z"
    pypi_version = "1.0"
    content = {
        "key": key,
        "last_check": last_check,
        "pypi_version": pypi_version,
    }

    Path(statefile_path).parent.mkdir()

    with open(statefile_path, "w") as f:
        json.dump(content, f)

    monkeypatch.setattr(sys, "prefix", key)
    state = outdated.SelfCheckState(str(cache_dir))

    assert state.state["last_check"] == last_check
    assert state.state["pypi_version"] == pypi_version


def test_self_check_state_writes_expected_statefile(monkeypatch, tmpdir):
    cache_dir = tmpdir / "cache_dir"
    cache_dir.mkdir()
    key = "helloworld"
    statefile_path = _get_statefile_path(str(cache_dir), key)

    last_check = datetime.datetime.strptime(
        "1970-01-02T11:00:00Z", outdated.SELFCHECK_DATE_FMT
    )
    pypi_version = "1.0"

    monkeypatch.setattr(sys, "prefix", key)
    state = outdated.SelfCheckState(str(cache_dir))

    state.save(pypi_version, last_check)
    with open(statefile_path) as f:
        saved = json.load(f)

    expected = {
        "key": key,
        "last_check": last_check.strftime(outdated.SELFCHECK_DATE_FMT),
        "pypi_version": pypi_version,
    }
    assert expected == saved
