from __future__ import annotations

import logging

import pytest

from pip._internal.commands.show import _PackageInfo, print_results


def _package_info(metadata_version: str) -> _PackageInfo:
    return _PackageInfo(
        name="example",
        version="1.0",
        location="/loc",
        editable_project_location=None,
        requires=[],
        required_by=[],
        installer="pip",
        metadata_version=metadata_version,
        classifiers=[],
        summary="",
        homepage="",
        project_urls=[],
        author="",
        author_email="",
        license="MIT",
        license_expression="MIT OR Apache-2.0",
        entry_points=[],
        files=None,
    )


@pytest.mark.parametrize(
    "metadata_version, expected, unexpected",
    [
        ("", "License: MIT", "License-Expression: MIT OR Apache-2.0"),
        ("2.4", "License-Expression: MIT OR Apache-2.0", "License: MIT"),
    ],
)
def test_print_results_license_for_metadata_version(
    caplog: pytest.LogCaptureFixture,
    metadata_version: str,
    expected: str,
    unexpected: str,
) -> None:
    caplog.set_level(logging.INFO)

    assert print_results(
        [_package_info(metadata_version)], list_files=False, verbose=False
    )

    messages = [record.getMessage() for record in caplog.records]
    assert expected in messages
    assert unexpected not in messages
