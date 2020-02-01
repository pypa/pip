from pip._internal.models.direct_url import (
    ArchiveInfo,
    DirectUrl,
    DirInfo,
    VcsInfo,
)
from pip._internal.utils.direct_url_helpers import (
    direct_url_as_pep440_direct_reference,
)


def test_as_pep440_requirement_archive():
    direct_url = DirectUrl(
        url="file:///home/user/archive.tgz",
        info=ArchiveInfo(),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ file:///home/user/archive.tgz"
    )
    direct_url.subdirectory = "subdir"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ file:///home/user/archive.tgz#subdirectory=subdir"
    )
    direct_url.info.hash = "sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ file:///home/user/archive.tgz"
        "#sha1=1b8c5bc61a86f377fea47b4276c8c8a5842d2220&subdirectory=subdir"
    )


def test_as_pep440_requirement_dir():
    direct_url = DirectUrl(
        url="file:///home/user/project",
        info=DirInfo(editable=False),
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ file:///home/user/project"
    )


def test_as_pep440_requirement_vcs():
    direct_url = DirectUrl(
        url="https:///g.c/u/p.git",
        info=VcsInfo(
            vcs="git", commit_id="1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
        )
    )
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ git+https:///g.c/u/p.git"
        "@1b8c5bc61a86f377fea47b4276c8c8a5842d2220"
    )
    direct_url.subdirectory = "subdir"
    direct_url.validate()
    assert (
        direct_url_as_pep440_direct_reference(direct_url, "pkg") ==
        "pkg @ git+https:///g.c/u/p.git"
        "@1b8c5bc61a86f377fea47b4276c8c8a5842d2220#subdirectory=subdir"
    )
