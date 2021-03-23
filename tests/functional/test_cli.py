"""Basic CLI functionality checks.
"""
from textwrap import dedent

import pytest


@pytest.mark.parametrize("entrypoint", [
    ("fake_pip = pip._internal.main:main",),
    ("fake_pip = pip._internal:main",),
    ("fake_pip = pip:main",),
])
def test_entrypoints_work(entrypoint, script):
    fake_pkg = script.temp_path / "fake_pkg"
    fake_pkg.mkdir()
    fake_pkg.joinpath("setup.py").write_text(dedent("""
    from setuptools import setup

    setup(
        name="fake-pip",
        version="0.1.0",
        entry_points={{
            "console_scripts": [
                {!r}
            ]
        }}
    )
    """.format(entrypoint)))

    script.pip("install", "-vvv", str(fake_pkg))
    result = script.pip("-V")
    result2 = script.run("fake_pip", "-V", allow_stderr_warning=True)
    assert result.stdout == result2.stdout
    assert "old script wrapper" in result2.stderr


@pytest.mark.parametrize(
    "extras",
    ["", "[with2]", "[with3]", "[with2,with3]"]
)
def test_entrypoints_with_extras_work(extras, script):
    fake_pkg = script.temp_path / "fake_pkg"
    fake_pkg.mkdir()
    fake_pkg.joinpath("setup.py").write_text(dedent("""
    from setuptools import setup

    setup(
        name="fake-pip",
        version="0.1.0",
        entry_points={
            "console_scripts": [
                "fake_pip = pip:main",
                "fake_pip2 = pip:main [with2]",
                "fake_pip3 = pip:main [with2,with3]",
            ]
        },
        extras_require={
            "with2": [],
            "with3": [],
        }
    )
    """))

    script.pip("install", "-vvv", "wheel")
    install_result = script.pip("install", "-vvv", f"{fake_pkg}{extras}")
    assert "Using legacy 'setup.py install'" not in install_result.stdout

    result = script.pip("-V")

    assert "venv/bin/fake_pip" in install_result.files_created
    result1 = script.run("fake_pip", "-V", allow_stderr_warning=True)
    assert result.stdout == result1.stdout
    assert "old script wrapper" in result1.stderr

    if "with2" in extras:
        assert "venv/bin/fake_pip2" in install_result.files_created
        result2 = script.run("fake_pip2", "-V", allow_stderr_warning=True)
        assert result.stdout == result2.stdout
        assert "old script wrapper" in result2.stderr
    else:
        assert "venv/bin/fake_pip2" not in install_result.files_created
        with pytest.raises(FileNotFoundError):
            result2 = script.run("fake_pip2", "-V", allow_stderr_warning=True)

    if "with2" in extras or "with3" in extras:
        assert "venv/bin/fake_pip3" in install_result.files_created
        result3 = script.run("fake_pip3", "-V", allow_stderr_warning=True)
        assert result.stdout == result3.stdout
        assert "old script wrapper" in result3.stderr
    else:
        assert "venv/bin/fake_pip3" not in install_result.files_created
        with pytest.raises(FileNotFoundError):
            result2 = script.run("fake_pip3", "-V", allow_stderr_warning=True)


def test_entrypoints_with_extras_incremental(script):
    fake_pkg = script.temp_path / "fake_pkg"
    fake_pkg.mkdir()
    fake_pkg.joinpath("setup.py").write_text(dedent("""
    from setuptools import setup

    setup(
        name="fake-pip",
        version="0.1.0",
        entry_points={
            "console_scripts": [
                "fake_pip = pip:main",
                "fake_pip2 = pip:main [with2]",
                "fake_pip3 = pip:main [with2,with3]",
            ]
        },
        extras_require={
            "with2": [],
            "with3": [],
        }
    )
    """))
    script.pip("install", "-vvv", "wheel")

    install_result = script.pip("install", "-vvv", f"{fake_pkg}")
    assert "Using legacy 'setup.py install'" not in install_result.stdout
    script.run("fake_pip", "-V", allow_stderr_warning=True)
    with pytest.raises(FileNotFoundError):
        script.run("fake_pip2", "-V", allow_stderr_warning=True)
    with pytest.raises(FileNotFoundError):
        script.run("fake_pip3", "-V", allow_stderr_warning=True)

    install_result = script.pip("install", "-vvv", f"{fake_pkg}[with3]")
    script.run("fake_pip", "-V", allow_stderr_warning=True)
    with pytest.raises(FileNotFoundError):
        script.run("fake_pip2", "-V", allow_stderr_warning=True)
    script.run("fake_pip3", "-V", allow_stderr_warning=True)

    install_result = script.pip("install", "-vvv", f"{fake_pkg}[with2]")
    script.run("fake_pip", "-V", allow_stderr_warning=True)
    script.run("fake_pip2", "-V", allow_stderr_warning=True)
    script.run("fake_pip3", "-V", allow_stderr_warning=True)
