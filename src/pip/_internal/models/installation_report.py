from typing import Any, Dict, Sequence

from pip._internal.req.req_install import InstallRequirement


class InstallationReport:
    def __init__(self, install_requirements: Sequence[InstallRequirement]):
        self._install_requirements = install_requirements

    @classmethod
    def _install_req_to_dict(cls, ireq: InstallRequirement) -> Dict[str, Any]:
        assert ireq.download_info, f"No download_info for {ireq}"
        res = {
            # PEP 610 json for the download URL. download_info.archive_info.hash may
            # be absent when the requirement was installed from the wheel cache
            # and the cache entry was populated by an older pip version that did not
            # record origin.json.
            "download_info": ireq.download_info.to_dict(),
            # is_direct is true if the requirement was a direct URL reference (which
            # includes editable requirements), and false if the requirement was
            # downloaded from a PEP 503 index or --find-links.
            "is_direct": bool(ireq.original_link),
            # requested is true if the requirement was specified by the user (aka
            # top level requirement), and false if it was installed as a dependency of a
            # requirement. https://peps.python.org/pep-0376/#requested
            "requested": ireq.user_supplied,
            # PEP 566 json encoding for metadata
            # https://www.python.org/dev/peps/pep-0566/#json-compatible-metadata
            "metadata": ireq.get_dist().metadata_dict,
        }
        return res

    def to_dict(self) -> Dict[str, Any]:
        return {
            "install": {
                ireq.get_dist().metadata["Name"]: self._install_req_to_dict(ireq)
                for ireq in self._install_requirements
            }
        }
