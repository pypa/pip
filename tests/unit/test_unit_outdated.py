import datetime
import os
import sys
from contextlib import contextmanager

import freezegun
import pretend
import pytest
from pip._vendor import lockfile

from pip._internal.index import InstallationCandidate
from pip._internal.utils import outdated


class MockPackageFinder(object):

    BASE_URL = 'https://pypi.python.org/simple/pip-{0}.tar.gz'
    PIP_PROJECT_NAME = 'pip'
    INSTALLATION_CANDIDATES = [
        InstallationCandidate(PIP_PROJECT_NAME, '6.9.0',
                              BASE_URL.format('6.9.0')),
        InstallationCandidate(PIP_PROJECT_NAME, '3.3.1',
                              BASE_URL.format('3.3.1')),
        InstallationCandidate(PIP_PROJECT_NAME, '1.0',
                              BASE_URL.format('1.0')),
    ]

    def __init__(self, *args, **kwargs):
        pass

    def find_all_candidates(self, project_name):
        return self.INSTALLATION_CANDIDATES


def _options():
    ''' Some default options that we pass to outdated.pip_version_check '''
    return pretend.stub(
        find_links=False, extra_index_urls=[], index_url='default_url',
        pre=False, trusted_hosts=False, process_dependency_links=False,
    )


@pytest.mark.parametrize(
    [
        'stored_time',
        'installed_ver',
        'new_ver',
        'check_if_upgrade_required',
        'check_warn_logs',
    ],
    [
        # Test we return None when installed version is None
        ('1970-01-01T10:00:00Z', None, '1.0', False, False),
        # Need an upgrade - upgrade warning should print
        ('1970-01-01T10:00:00Z', '1.0', '6.9.0', True, True),
        # No upgrade - upgrade warning should not print
        ('1970-01-9T10:00:00Z', '6.9.0', '6.9.0', False, False),
    ]
)
def test_pip_version_check(monkeypatch, stored_time, installed_ver, new_ver,
                           check_if_upgrade_required, check_warn_logs):
    monkeypatch.setattr(outdated, 'get_installed_version',
                        lambda name: installed_ver)
    monkeypatch.setattr(outdated, 'PackageFinder', MockPackageFinder)
    monkeypatch.setattr(outdated.logger, 'warning',
                        pretend.call_recorder(lambda *a, **kw: None))
    monkeypatch.setattr(outdated.logger, 'debug',
                        pretend.call_recorder(lambda s, exc_info=None: None))

    fake_state = pretend.stub(
        state={"last_check": stored_time, 'pypi_version': installed_ver},
        save=pretend.call_recorder(lambda v, t: None),
    )
    monkeypatch.setattr(
        outdated, 'load_selfcheck_statefile', lambda: fake_state
    )

    with freezegun.freeze_time(
            "1970-01-09 10:00:00",
            ignore=[
                "six.moves",
                "pip._vendor.six.moves",
                "pip._vendor.requests.packages.urllib3.packages.six.moves",
            ]):
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


def test_virtualenv_state(monkeypatch):
    CONTENT = '{"last_check": "1970-01-02T11:00:00Z", "pypi_version": "1.0"}'
    fake_file = pretend.stub(
        read=pretend.call_recorder(lambda: CONTENT),
        write=pretend.call_recorder(lambda s: None),
    )

    @pretend.call_recorder
    @contextmanager
    def fake_open(filename, mode='r'):
        yield fake_file

    monkeypatch.setattr(outdated, 'open', fake_open, raising=False)

    monkeypatch.setattr(outdated, 'running_under_virtualenv',
                        pretend.call_recorder(lambda: True))

    monkeypatch.setattr(sys, 'prefix', 'virtually_env')

    state = outdated.load_selfcheck_statefile()
    state.save('2.0', datetime.datetime.utcnow())

    assert len(outdated.running_under_virtualenv.calls) == 1

    expected_path = os.path.join('virtually_env', 'pip-selfcheck.json')
    assert fake_open.calls == [
        pretend.call(expected_path),
        pretend.call(expected_path, 'w'),
    ]

    # json.dumps will call this a number of times
    assert len(fake_file.write.calls)


def test_global_state(monkeypatch, tmpdir):
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

    monkeypatch.setattr(outdated, 'running_under_virtualenv',
                        pretend.call_recorder(lambda: False))

    cache_dir = tmpdir / 'cache_dir'
    monkeypatch.setattr(outdated, 'USER_CACHE_DIR', cache_dir)
    monkeypatch.setattr(sys, 'prefix', tmpdir / 'pip_prefix')

    state = outdated.load_selfcheck_statefile()
    state.save('2.0', datetime.datetime.utcnow())

    assert len(outdated.running_under_virtualenv.calls) == 1

    expected_path = cache_dir / 'selfcheck.json'
    assert fake_lock.calls == [pretend.call(expected_path)]

    assert fake_open.calls == [
        pretend.call(expected_path),
        pretend.call(expected_path),
        pretend.call(expected_path, 'w'),
    ]

    # json.dumps will call this a number of times
    assert len(fake_file.write.calls)
