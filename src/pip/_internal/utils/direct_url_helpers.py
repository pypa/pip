from typing import List, Optional

from pip._internal.models.direct_url import ArchiveInfo, DirectUrl, DirInfo, VcsInfo
from pip._internal.models.link import Link, links_equivalent
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import vcs


def direct_url_as_pep440_direct_reference(direct_url: DirectUrl, name: str) -> str:
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
        requirement += direct_url.url
    if direct_url.subdirectory:
        fragments.append("subdirectory=" + direct_url.subdirectory)
    if fragments:
        requirement += "#" + "&".join(fragments)
    return requirement


def direct_url_for_editable(source_dir: str) -> DirectUrl:
    return DirectUrl(
        url=path_to_url(source_dir),
        info=DirInfo(editable=True),
    )


def direct_url_from_link(
    link: Link, source_dir: Optional[str] = None, link_is_in_wheel_cache: bool = False
) -> DirectUrl:
    if link.is_vcs:
        vcs_backend = vcs.get_backend_for_scheme(link.scheme)
        assert vcs_backend
        url, requested_revision, _ = vcs_backend.get_url_rev_and_auth(
            link.url_without_fragment
        )
        # For VCS links, we need to find out and add commit_id.
        if link_is_in_wheel_cache:
            # If the requested VCS link corresponds to a cached
            # wheel, it means the requested revision was an
            # immutable commit hash, otherwise it would not have
            # been cached. In that case we don't have a source_dir
            # with the VCS checkout.
            assert requested_revision
            commit_id = requested_revision
        else:
            # If the wheel was not in cache, it means we have
            # had to checkout from VCS to build and we have a source_dir
            # which we can inspect to find out the commit id.
            assert source_dir
            commit_id = vcs_backend.get_revision(source_dir)
        return DirectUrl(
            url=url,
            info=VcsInfo(
                vcs=vcs_backend.name,
                commit_id=commit_id,
                requested_revision=requested_revision,
            ),
            subdirectory=link.subdirectory_fragment,
        )
    elif link.is_existing_dir():
        return DirectUrl(
            url=link.url_without_fragment,
            info=DirInfo(),
            subdirectory=link.subdirectory_fragment,
        )
    else:
        hash = None
        hash_name = link.hash_name
        if hash_name:
            hash = f"{hash_name}={link.hash}"
        return DirectUrl(
            url=link.url_without_fragment,
            info=ArchiveInfo(hash=hash),
            subdirectory=link.subdirectory_fragment,
        )


def _link_from_direct_url(direct_url: DirectUrl) -> Link:
    """Create a link from given direct URL construct.

    This function is designed specifically for ``link_matches_direct_url``, and
    does NOT losslessly reconstruct the original link that produced the
    DirectUrl. Namely:

    * The auth part is ignored (since it does not affect link equivalency).
    * Only "subdirectory" and hash fragment parts are considered, and the
      ordering of the kept parts are not considered (since only their values
      affect link equivalency).

    .. seealso:: ``pip._internal.models.link.links_equivalent()``
    """
    url = direct_url.url
    hash_frag: Optional[str] = None

    direct_url_info = direct_url.info
    if isinstance(direct_url_info, VcsInfo):
        url = f"{url}@{direct_url_info.requested_revision}"
    elif isinstance(direct_url_info, ArchiveInfo):
        hash_frag = direct_url_info.hash

    fragment_parts: List[str] = []
    if direct_url.subdirectory is not None:
        fragment_parts.append(f"subdirectory={direct_url.subdirectory}")
    if hash_frag:
        fragment_parts.append(hash_frag)
    if fragment_parts:
        fragment = "&".join(fragment_parts)
        url = f"{url}#{fragment}"

    return Link(url)


def link_matches_direct_url(link: Link, direct_url: DirectUrl) -> bool:
    return links_equivalent(link, _link_from_direct_url(direct_url))
