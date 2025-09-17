"""Test that pip index versions handles invalid (non-PEP 440) wheel filenames.

This test was added for robustness after legacy wheel filename support
was removed in pip 25.3.
"""

import json
import textwrap
from pathlib import Path

from tests.lib import PipTestEnvironment
from tests.lib.wheel import make_wheel


def _create_test_index_with_invalid_wheels(
    tmpdir: Path, package_name: str = "pkg"
) -> Path:
    """Create a test index with both valid and invalid wheel filenames.

    Returns the path to the index directory.
    """
    # Create test index
    index_dir = tmpdir / "test_index"
    index_dir.mkdir()

    (index_dir / "index.html").write_text(
        textwrap.dedent(
            f"""\
        <!DOCTYPE html>
        <html>
          <body><a href="{package_name}/index.html">{package_name}</a></body>
        </html>
        """
        )
    )

    pkg_dir = index_dir / package_name
    pkg_dir.mkdir()

    valid_wheels = [
        (f"{package_name}-1.0.0-py3-none-any.whl", "1.0.0"),
        (f"{package_name}-2.0.0-py3-none-any.whl", "2.0.0"),
    ]
    invalid_wheels = [
        (f"{package_name}-3.0_1-py3-none-any.whl", "3.0"),  # underscore in version
        (f"{package_name}-_bad_-py3-none-any.wh", "1.0.0"),  # no version
        (
            f"{package_name}-5.0.0_build1-py3-none-any.whl",
            "5.0.0",
        ),  # underscore in build tag
    ]

    all_wheels = valid_wheels + invalid_wheels
    for wheel_name, version in all_wheels:
        wheel = make_wheel(name=package_name, version=version)
        wheel.save_to(pkg_dir / wheel_name)

    # Create package index
    links = [
        f'<a href="{wheel_name}">{wheel_name}</a><br/>' for wheel_name, _ in all_wheels
    ]
    (pkg_dir / "index.html").write_text(
        textwrap.dedent(
            f"""\
        <!DOCTYPE html>
        <html>
          <body>
            {''.join(links)}
          </body>
        </html>
        """
        )
    )

    return index_dir


def test_index_versions_ignores_invalid_wheel_names(
    script: PipTestEnvironment,
    tmpdir: Path,
) -> None:
    """Test that pip index versions ignores invalid wheel names."""
    index_dir = _create_test_index_with_invalid_wheels(tmpdir)

    # Run pip index versions with JSON output
    result = script.pip(
        "index", "versions", "pkg", "--json", "--index-url", index_dir.as_uri()
    )

    assert result.returncode == 0

    output = json.loads(result.stdout)
    assert output["name"] == "pkg"
    assert output["latest"] == "2.0.0"

    expected_versions = ["2.0.0", "1.0.0"]
    assert output["versions"] == expected_versions


def test_install_ignores_invalid_wheel_names(
    script: PipTestEnvironment,
    tmpdir: Path,
) -> None:
    """Test that pip install ignores invalid wheel names and installs valid ones."""
    index_dir = _create_test_index_with_invalid_wheels(tmpdir)

    # Run pip install - should ignore invalid wheels and install the latest valid one
    result = script.pip(
        "install", "pkg", "--no-cache-dir", "--index-url", index_dir.as_uri()
    )

    assert result.returncode == 0
    script.assert_installed(pkg="2.0.0")
