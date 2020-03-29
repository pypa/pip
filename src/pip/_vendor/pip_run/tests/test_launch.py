from __future__ import unicode_literals

import sys
import subprocess
import textwrap
import os

import pytest

from pip._vendor.pip_run import launch


def test_with_path(tmpdir, capfd):
    params = ['-c', 'import sys; sys.stdout.write("\\n".join(sys.path))']
    res = launch.with_path(str(tmpdir), params)
    assert res == 0
    out, err = capfd.readouterr()
    assert tmpdir in out.split(os.linesep)


def test_with_path_result_code(tmpdir):
    """
    result code should be non-zero on error
    """
    params = ['-c', "raise ValueError()"]
    res = launch.with_path(str(tmpdir), params)
    assert res > 0


@pytest.mark.xfail(reason="cleanup can't occur with execv; #4")
def test_with_path_overlay(tmpdir, capfd):
    params = ['-c', 'import sys; sys.stdout.write("\\n".join(sys.path))']
    # launch subprocess so as not to overlay the test process
    script = (
        textwrap.dedent(
            """
        import pip_run.launch
        pip_run.launch.with_path_overlay({tmpdir!r}, {params!r})
        print("cleanup")
    """
        )
        .strip()
        .replace('\n', '; ')
        .format(tmpdir=str(tmpdir), params=params)
    )
    subprocess.Popen([sys.executable, '-c', script]).wait()
    out, err = capfd.readouterr()
    assert str(tmpdir) in out.split(os.linesep)
    assert "cleanup" in out


@pytest.fixture
def clean_pythonpath(monkeypatch):
    monkeypatch.delitem(os.environ, 'PYTHONPATH', raising=False)


def test_build_env(clean_pythonpath):
    os.environ['PYTHONPATH'] = 'something'
    env = launch._build_env('else')
    expected = os.pathsep.join(('else', 'something'))
    assert env['PYTHONPATH'] == expected

    os.environ['PYTHONPATH'] = ''
    env = launch._build_env('something')
    assert env['PYTHONPATH'] == 'something'

    initial = os.pathsep.join(['something', 'else'])
    os.environ['PYTHONPATH'] = initial
    env = launch._build_env('a')
    expected = os.pathsep.join(['a', 'something', 'else'])
    assert env['PYTHONPATH'] == expected


def test_build_env_includes_pth_files(tmpdir, clean_pythonpath):
    """
    If during _build_env, there are .pth files in the target directory,
    they should be processed to include any paths indicated there.
    See #6 for rationale.
    """
    (tmpdir / 'foo.pth').write_text('pkg-1.0', encoding='utf-8')
    env = launch._build_env(str(tmpdir))
    expected = os.pathsep.join([str(tmpdir), str(tmpdir / 'pkg-1.0')])
    assert env['PYTHONPATH'] == expected
