import collections
import hashlib

import pytest

from pip._internal.utils.urls import path_to_url
from tests.lib import (
    create_basic_sdist_for_package,
    create_basic_wheel_for_package,
)

_AddedLink = collections.namedtuple(
    "_AddedLink", "url hash stem"
)

_FindLinks = collections.namedtuple(
    "_FindLinks", "index_html sdist_hash wheel_hash",
)


def _add_link_to_find(html_path, archive_path):
    archive_url = path_to_url(archive_path)
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    line = "<a href='{url}#sha256={hash}'>{stem}</a>\n".format(
        url=archive_url,
        hash=archive_hash,
        stem=archive_path.stem,
    )
    with open(html_path, "a") as f:
        f.write(line)

    return archive_hash


def _create_find_links(script):
    sdist_path = create_basic_sdist_for_package(script, "base", "0.1.0")
    wheel_path = create_basic_wheel_for_package(script, "base", "0.1.0")

    index_html = script.scratch_path / "index.html"
    sdist_hash = _add_link_to_find(index_html, sdist_path)
    wheel_hash = _add_link_to_find(index_html, wheel_path)

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


def test_new_resolver_use_specifier_from_constraints(script):
    find_links = _create_find_links(script)

    child_wheel = create_basic_wheel_for_package(
        script,
        "child",
        "1.0",
        depends=["base"],
    )
    child_hash = _add_link_to_find(find_links.index_html, child_wheel)

    constraints_txt = script.scratch_path / "constraints.txt"
    constraints_txt.write_text(
        "child==1.0 --hash=sha256:{child_hash}".format(child_hash=child_hash),
    )

    requirements_txt = script.scratch_path / "requirements.txt"
    requirements_txt.write_text(
        """
        -c {constraints_txt}
        base==0.1.0 --hash=sha256:{h}
        """.format(constraints_txt=constraints_txt, h=find_links.wheel_hash),
    )

    script.pip(
        "install",
        "--use-feature=2020-resolver",
        "--no-cache-dir",
        "--no-deps",
        "--no-index",
        "--find-links", find_links.index_html,
        "--requirement", requirements_txt,
    )
