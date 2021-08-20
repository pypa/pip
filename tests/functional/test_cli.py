"""Basic CLI functionality checks.
"""
from textwrap import dedent

import pytest


@pytest.mark.parametrize(
    "entrypoint",
    [
        ("fake_pip = pip._internal.main:main",),
        ("fake_pip = pip._internal:main",),
        ("fake_pip = pip:main",),
    ],
)
def test_entrypoints_work(entrypoint, script):
    fake_pkg = script.temp_path / "fake_pkg"
    fake_pkg.mkdir()
    fake_pkg.joinpath("setup.py").write_text(
        dedent(
            """
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
    """.format(
                entrypoint
            )
        )
    )

    script.pip("install", "-vvv", str(fake_pkg))
    result = script.pip("-V")
    result2 = script.run("fake_pip", "-V", allow_stderr_warning=True)
    assert result.stdout == result2.stdout
    assert "old script wrapper" in result2.stderr
