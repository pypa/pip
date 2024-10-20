import re
from typing import List

import pytest

from pip._vendor.packaging.version import Version

from pip._internal.commands.debug import create_vendor_txt_map
from pip._internal.utils import compatibility_tags

from tests.lib import PipTestEnvironment


@pytest.mark.parametrize(
    "expected_text",
    [
        "sys.executable: ",
        "sys.getdefaultencoding: ",
        "sys.getfilesystemencoding: ",
        "locale.getpreferredencoding: ",
        "sys.platform: ",
        "sys.implementation:",
        "'cert' config value: ",
        "REQUESTS_CA_BUNDLE: ",
        "CURL_CA_BUNDLE: ",
        "pip._vendor.certifi.where(): ",
        "pip._vendor.DEBUNDLED: ",
        "vendored library versions:",
    ],
)
def test_debug(script: PipTestEnvironment, expected_text: str) -> None:
    """
    Check that certain strings are present in the output.
    """
    args = ["debug"]
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    assert expected_text in stdout


def test_debug__library_versions(script: PipTestEnvironment) -> None:
    """
    Check the library versions normal output.
    """
    args = ["debug"]
    result = script.pip(*args, allow_stderr_warning=True)
    print(result.stdout)

    vendored_versions = create_vendor_txt_map()
    for name, value in vendored_versions.items():
        match = re.search(rf"{name}==(\S+)", result.stdout)
        assert match is not None, f"Could not find {name} in output"
        assert Version(match.group(1)) == Version(value)


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--verbose"],
    ],
)
def test_debug__tags(script: PipTestEnvironment, args: List[str]) -> None:
    """
    Check the compatible tag output.
    """
    args = ["debug"] + args
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    tags = compatibility_tags.get_supported()
    expected_tag_header = f"Compatible tags: {len(tags)}"
    assert expected_tag_header in stdout

    show_verbose_note = "--verbose" not in args
    assert (
        "...\n  [First 10 tags shown. Pass --verbose to show all.]" in stdout
    ) == show_verbose_note


@pytest.mark.parametrize(
    "args, expected",
    [
        (["--python-version", "3.7"], "(target: version_info='3.7')"),
    ],
)
def test_debug__target_options(
    script: PipTestEnvironment, args: List[str], expected: str
) -> None:
    """
    Check passing target-related options.
    """
    args = ["debug"] + args
    result = script.pip(*args, allow_stderr_warning=True)
    stdout = result.stdout

    assert "Compatible tags: " in stdout
    assert expected in stdout
