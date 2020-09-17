import collections
import hashlib

import pytest

from pip._internal.utils.urls import path_to_url
from tests.lib import (
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
)

_FindLinks = collections.namedtuple(
    "_FindLinks", "index_html sdist_hash wheel_hash",
)


def _create_find_links(script):
    sdist_path = create_basic_sdist_for_package(script, "base", "0.1.0")
    wheel_path = create_basic_wheel_for_package(script, "base", "0.1.0")

    sdist_hash = hashlib.sha256(sdist_path.read_bytes()).hexdigest()
    wheel_hash = hashlib.sha256(wheel_path.read_bytes()).hexdigest()

    index_html = script.scratch_path / "index.html"
    index_html.write_text(
        """
        <a href="{sdist_url}#sha256={sdist_hash}">{sdist_path.stem}</a>
        <a href="{wheel_url}#sha256={wheel_hash}">{wheel_path.stem}</a>
        """.format(
            sdist_url=path_to_url(sdist_path),
            sdist_hash=sdist_hash,
            sdist_path=sdist_path,
            wheel_url=path_to_url(wheel_path),
            wheel_hash=wheel_hash,
            wheel_path=wheel_path,
        )
    )

    return _FindLinks(index_html, sdist_hash, wheel_hash)


@pytest.mark.parametrize(
    "requirements_template, message",
    [
        (
            """
            base==0.1.0 --hash=sha256:{sdist_hash} --hash=sha256:{wheel_hash}
            base==0.1.0 --hash=sha256:{sdist_hash} --hash=sha256:{wheel_hash}
            """,
            "Checked 2 links for project {name!r} against 2 hashes "
            "(2 matches, 0 no digest): discarding no candidates",
        ),
        (
            # Different hash lists are intersected.
            """
            base==0.1.0 --hash=sha256:{sdist_hash} --hash=sha256:{wheel_hash}
            base==0.1.0 --hash=sha256:{sdist_hash}
            """,
            "Checked 2 links for project {name!r} against 1 hashes "
            "(1 matches, 0 no digest): discarding 1 non-matches",
        ),
    ],
    ids=["identical", "intersect"],
)
def test_new_resolver_hash_intersect(script, requirements_template, message):
    find_links = _create_find_links(script)

    requirements_txt = script.scratch_path / "requirements.txt"
    requirements_txt.write_text(
        requirements_template.format(
            sdist_hash=find_links.sdist_hash,
            wheel_hash=find_links.wheel_hash,
        ),
    )

    result = script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-deps",
        "--no-index",
        "--find-links", find_links.index_html,
        "--verbose",
        "--requirement", requirements_txt,
    )

    assert message.format(name=u"base") in result.stdout, str(result)


def test_new_resolver_hash_intersect_from_constraint(script):
    find_links = _create_find_links(script)

    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(
        "base==0.1.0 --hash=sha256:{sdist_hash}".format(
            sdist_hash=find_links.sdist_hash,
        ),
    )
    requirements_txt = script.scratch_path / "requirements.txt"
    requirements_txt.write_text(
        """
        base==0.1.0 --hash=sha256:{sdist_hash} --hash=sha256:{wheel_hash}
        """.format(
            sdist_hash=find_links.sdist_hash,
            wheel_hash=find_links.wheel_hash,
        ),
    )

    result = script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-deps",
        "--no-index",
        "--find-links", find_links.index_html,
        "--verbose",
        "--constraint", constraints_txt,
        "--requirement", requirements_txt,
    )

    message = (
        "Checked 2 links for project {name!r} against 1 hashes "
        "(1 matches, 0 no digest): discarding 1 non-matches"
    ).format(name=u"base")
    assert message in result.stdout, str(result)


@pytest.mark.parametrize(
    "requirements_template, constraints_template",
    [
        (
            """
            base==0.1.0 --hash=sha256:{sdist_hash}
            base==0.1.0 --hash=sha256:{wheel_hash}
            """,
            "",
        ),
        (
            "base==0.1.0 --hash=sha256:{sdist_hash}",
            "base==0.1.0 --hash=sha256:{wheel_hash}",
        ),
    ],
    ids=["both-requirements", "one-each"],
)
def test_new_resolver_hash_intersect_empty(
    script, requirements_template, constraints_template,
):
    find_links = _create_find_links(script)

    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(
        constraints_template.format(
            sdist_hash=find_links.sdist_hash,
            wheel_hash=find_links.wheel_hash,
        ),
    )

    requirements_txt = script.scratch_path / "requirements.txt"
    requirements_txt.write_text(
        requirements_template.format(
            sdist_hash=find_links.sdist_hash,
            wheel_hash=find_links.wheel_hash,
        ),
    )

    result = script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-deps",
        "--no-index",
        "--find-links", find_links.index_html,
        "--constraint", constraints_txt,
        "--requirement", requirements_txt,
        expect_error=True,
    )

    assert (
        "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE."
    ) in result.stderr, str(result)


def test_new_resolver_hash_intersect_empty_from_constraint(script):
    find_links = _create_find_links(script)

    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(
        """
        base==0.1.0 --hash=sha256:{sdist_hash}
        base==0.1.0 --hash=sha256:{wheel_hash}
        """.format(
            sdist_hash=find_links.sdist_hash,
            wheel_hash=find_links.wheel_hash,
        ),
    )

    result = script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-deps",
        "--no-index",
        "--find-links", find_links.index_html,
        "--constraint", constraints_txt,
        "base==0.1.0",
        expect_error=True,
    )

    message = (
        "Hashes are required in --require-hashes mode, but they are missing "
        "from some requirements."
    )
    assert message in result.stderr, str(result)
