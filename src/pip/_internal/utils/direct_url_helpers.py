from pip._internal.models.direct_url import (
    ArchiveInfo,
    DirectUrl,
    DirInfo,
    VcsInfo,
)


def direct_url_as_pep440_direct_reference(direct_url, name):
    # type: (DirectUrl, str) -> str
    """Convert a DirectUrl to a pip requirement string."""
    direct_url.validate()  # if invalid, this is a pip bug
    requirement = name + " @ "
    fragments = []
    if isinstance(direct_url.info, VcsInfo):
        requirement += "{}+{}@{}".format(
            direct_url.info.vcs, direct_url.url, direct_url.info.commit_id
        )
    elif isinstance(direct_url.info, ArchiveInfo):
        requirement += direct_url.url
        if direct_url.info.hash:
            fragments.append(direct_url.info.hash)
    else:
        assert isinstance(direct_url.info, DirInfo)
        # pip should never reach this point for editables, since
        # pip freeze inspects the editable project location to produce
        # the requirement string
        assert not direct_url.info.editable
        requirement += direct_url.url
    if direct_url.subdirectory:
        fragments.append("subdirectory=" + direct_url.subdirectory)
    if fragments:
        requirement += "#" + "&".join(fragments)
    return requirement
