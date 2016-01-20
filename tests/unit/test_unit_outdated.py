import sys
import datetime
import os
from contextlib import contextmanager

import freezegun
import pytest
import pretend

from pip._vendor import lockfile
from pip.utils import outdated


@pytest.mark.parametrize(
    ['stored_time', 'newver', 'check', 'warn'],
    [
        ('1970-01-01T10:00:00Z', '2.0', True, True),
        ('1970-01-01T10:00:00Z', '1.0', True, False),
        ('1970-01-06T10:00:00Z', '1.0', False, False),
        ('1970-01-06T10:00:00Z', '2.0', False, True),
    ]
)
def test_pip_version_check(monkeypatch, stored_time, newver, check, warn):
    monkeypatch.setattr(outdated, 'get_installed_version', lambda name: '1.0')

    resp = pretend.stub(
        raise_for_status=pretend.call_recorder(lambda: None),
        json=pretend.call_recorder(lambda: {"releases": {newver: {}}}),
    )
    session = pretend.stub(
        get=pretend.call_recorder(lambda u, headers=None: resp),
    )

    fake_state = pretend.stub(
        state={"last_check": stored_time, 'pypi_version': '1.0'},
        save=pretend.call_recorder(lambda v, t: None),
    )

    monkeypatch.setattr(
        outdated, 'load_selfcheck_statefile', lambda: fake_state
    )

    monkeypatch.setattr(outdated.logger, 'warning',
                        pretend.call_recorder(lambda *a, **kw: None))
    monkeypatch.setattr(outdated.logger, 'debug',
                        pretend.call_recorder(lambda s, exc_info=None: None))

    with freezegun.freeze_time(
            "1970-01-09 10:00:00",
            ignore=[
                "six.moves",
                "pip._vendor.six.moves",
                "pip._vendor.requests.packages.urllib3.packages.six.moves",
            ]):
        outdated.pip_version_check(session)

    assert not outdated.logger.debug.calls

    if check:
        assert session.get.calls == [pretend.call(
            "https://pypi.python.org/pypi/pip/json",
            headers={"Accept": "application/json"}
        )]
        assert fake_state.save.calls == [
            pretend.call(newver, datetime.datetime(1970, 1, 9, 10, 00, 00)),
        ]
        if warn:
            assert len(outdated.logger.warning.calls) == 1
        else:
            assert len(outdated.logger.warning.calls) == 0
    else:
        assert session.get.calls == []
        assert fake_state.save.calls == []


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


def test_global_state(monkeypatch):
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

    monkeypatch.setattr(outdated, 'USER_CACHE_DIR', 'cache_dir')
    monkeypatch.setattr(sys, 'prefix', 'pip_prefix')

    state = outdated.load_selfcheck_statefile()
    state.save('2.0', datetime.datetime.utcnow())

    assert len(outdated.running_under_virtualenv.calls) == 1

    expected_path = os.path.join('cache_dir', 'selfcheck.json')
    assert fake_lock.calls == [pretend.call(expected_path)]

    assert fake_open.calls == [
        pretend.call(expected_path),
        pretend.call(expected_path),
        pretend.call(expected_path, 'w'),
    ]

    # json.dumps will call this a number of times
    assert len(fake_file.write.calls)
