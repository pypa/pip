import sys
import datetime
import os
from contextlib import contextmanager

import pytest
import pretend

import pip
from pip._vendor import lockfile
from pip import util


@pytest.mark.parametrize(
    ['stored_time', 'newver', 'check', 'warn'],
    [
        ('1970-01-01T10:00:00Z', '2.0', True, True),
        ('1970-01-01T10:00:00Z', '1.0', True, False),
        ('1970-01-06T10:00:00Z', '1.0', False, False),
        ('1970-01-06T10:00:00Z', '2.0', False, True),
    ]
)
def test_self_check(monkeypatch, stored_time, newver, check, warn):
    monkeypatch.setattr(pip, '__version__', '1.0')

    resp = pretend.stub(
        raise_for_status=pretend.call_recorder(lambda: None),
        json=pretend.call_recorder(lambda: {"info": {"version": newver}}),
    )
    session = pretend.stub(
        get=pretend.call_recorder(lambda u, headers=None: resp),
    )

    fake_state = pretend.stub(
        state={"last_check": stored_time, 'pypi_version': '1.0'},
        save=pretend.call_recorder(lambda v, t: None),
    )

    monkeypatch.setattr(util, 'load_selfcheck_statefile', lambda: fake_state)

    fake_now = datetime.datetime(1970, 1, 9, 10, 00, 00)

    fake_datetime = pretend.stub(
        utcnow=pretend.call_recorder(lambda: fake_now),
        strptime=datetime.datetime.strptime,
    )
    monkeypatch.setattr(datetime, 'datetime', fake_datetime)

    monkeypatch.setattr(util.logger, 'warn',
                        pretend.call_recorder(lambda s: None))
    monkeypatch.setattr(util.logger, 'debug',
                        pretend.call_recorder(lambda s, exc_info=None: None))

    util.self_check(session)

    assert not util.logger.debug.calls

    if check:
        assert session.get.calls == [pretend.call(
            "https://pypi.python.org/pypi/pip/json",
            headers={"Accept": "application/json"}
        )]
        assert fake_state.save.calls == [pretend.call(newver, fake_now)]
        if warn:
            assert len(util.logger.warn.calls) == 1
        else:
            assert len(util.logger.warn.calls) == 0
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

    monkeypatch.setattr(util, 'open', fake_open, raising=False)

    monkeypatch.setattr(util, 'running_under_virtualenv',
                        pretend.call_recorder(lambda: True))

    monkeypatch.setattr(sys, 'prefix', 'virtually_env')

    state = util.load_selfcheck_statefile()
    state.save('2.0', datetime.datetime.utcnow())

    assert len(util.running_under_virtualenv.calls) == 1

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

    monkeypatch.setattr(util, 'open', fake_open, raising=False)

    @pretend.call_recorder
    @contextmanager
    def fake_lock(filename):
        yield

    monkeypatch.setattr(lockfile, 'LockFile', fake_lock)

    monkeypatch.setattr(util, 'running_under_virtualenv',
                        pretend.call_recorder(lambda: False))

    monkeypatch.setattr(util, 'USER_CACHE_DIR', 'cache_dir')
    monkeypatch.setattr(sys, 'prefix', 'pip_prefix')

    state = util.load_selfcheck_statefile()
    state.save('2.0', datetime.datetime.utcnow())

    assert len(util.running_under_virtualenv.calls) == 1

    expected_path = os.path.join('cache_dir', 'selfcheck.json')
    assert fake_lock.calls == [pretend.call(expected_path)]

    assert fake_open.calls == [
        pretend.call(expected_path),
        pretend.call(expected_path),
        pretend.call(expected_path, 'w'),
    ]

    # json.dumps will call this a number of times
    assert len(fake_file.write.calls)
