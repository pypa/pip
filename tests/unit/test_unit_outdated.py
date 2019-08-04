import datetime
import os
import sys
from contextlib import contextmanager

import freezegun
import pretend
import pytest
from pip._vendor import lockfile, pkg_resources

from pip._internal.index import InstallationCandidate
from pip._internal.utils import outdated


class MockFoundCandidates(object):
    def __init__(self, best):
        self._best = best

    def get_best(self):
        return self._best


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

    def find_candidates(self, project_name):
        return MockFoundCandidates(self.INSTALLATION_CANDIDATES[0])


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
        no_index=False, pre=False, trusted_hosts=False, cache_dir='',
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
    monkeypatch.setattr(outdated.logger, 'warning',
                        pretend.call_recorder(lambda *a, **kw: None))
    monkeypatch.setattr(outdated.logger, 'debug',
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
        latest_pypi_version = outdated.pip_version_check(None, _options())

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
        assert not outdated.logger.debug.calls
        # See that save was not called
        assert fake_state.save.calls == []

    # Ensure we warn the user or not
    if check_warn_logs:
        assert len(outdated.logger.warning.calls) == 1
    else:
        assert len(outdated.logger.warning.calls) == 0


def test_self_check_state(monkeypatch, tmpdir):
    CONTENT = '''{"pip_prefix": {"last_check": "1970-01-02T11:00:00Z",
        "pypi_version": "1.0"}}'''
    fake_file = pretend.stub(
        read=pretend.call_recorder(lambda: CONTENT),
        write=pretend.call_recorder(lambda s: None),
    )

    @pretend.call_recorder
    @contextmanager
    def fake_open(filename, mode='r'):
        yield fake_file

    monkeypatch.setattr(outdated, 'open', fake_open, raising=False)

    @pretend.call_recorder
    @contextmanager
    def fake_lock(filename):
        yield

    monkeypatch.setattr(outdated, "check_path_owner", lambda p: True)

    monkeypatch.setattr(lockfile, 'LockFile', fake_lock)
    monkeypatch.setattr(os.path, "exists", lambda p: True)

    cache_dir = tmpdir / 'cache_dir'
    monkeypatch.setattr(sys, 'prefix', tmpdir / 'pip_prefix')

    state = outdated.SelfCheckState(cache_dir=cache_dir)
    state.save('2.0', datetime.datetime.utcnow())

    expected_path = cache_dir / 'selfcheck.json'
    assert fake_lock.calls == [pretend.call(expected_path)]

    assert fake_open.calls == [
        pretend.call(expected_path),
        pretend.call(expected_path),
        pretend.call(expected_path, 'w'),
    ]

    # json.dumps will call this a number of times
    assert len(fake_file.write.calls)


def test_self_check_state_no_cache_dir():
    state = outdated.SelfCheckState(cache_dir=False)
    assert state.state == {}
    assert state.statefile_path is None
