import collections
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Generator, List, Optional, Sequence, Tuple

from pip._internal.utils.logging import indent_log

from .req_file import parse_requirements
from .req_install import InstallRequirement
from .req_set import RequirementSet

__all__ = [
    "RequirementSet",
    "InstallRequirement",
    "parse_requirements",
    "install_given_reqs",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstallationResult:
    name: str


def _validate_requirements(
    requirements: List[InstallRequirement],
) -> Generator[Tuple[str, InstallRequirement], None, None]:
    for req in requirements:
        assert req.name, f"invalid to-be-installed requirement: {req}"
        yield req.name, req


def install_requirement(
    req_name,
    requirement,
    global_options,
    root,
    home,
    prefix,
    warn_script_location,
    use_user_site,
    pycompile,
):
    if requirement.should_reinstall:
        logger.info("Attempting uninstall: %s", req_name)
        with indent_log():
            uninstalled_pathset = requirement.uninstall(auto_confirm=True)
    else:
        uninstalled_pathset = None

    try:
        print(f"installing [{threading.get_ident()}]: {req_name}")
        requirement.install(
            global_options,
            root=root,
            home=home,
            prefix=prefix,
            warn_script_location=warn_script_location,
            use_user_site=use_user_site,
            pycompile=pycompile,
        )
        print(f"  done [{threading.get_ident()}]: {req_name}")
    except Exception:
        # if install did not succeed, rollback previous uninstall
        if uninstalled_pathset and not requirement.install_succeeded:
            uninstalled_pathset.rollback()
        raise
    else:
        if uninstalled_pathset and requirement.install_succeeded:
            uninstalled_pathset.commit()

    return req_name


def install_given_reqs(
    requirements: List[InstallRequirement],
    global_options: Sequence[str],
    root: Optional[str],
    home: Optional[str],
    prefix: Optional[str],
    warn_script_location: bool,
    use_user_site: bool,
    pycompile: bool,
) -> List[InstallationResult]:
    """
    Install everything in the given list.

    (to be called after having downloaded and unpacked the packages)
    """
    to_install = collections.OrderedDict(_validate_requirements(requirements))

    if to_install:
        logger.info(
            "Installing collected packages: %s",
            ", ".join(to_install.keys()),
        )

    installed = []
    import time

    start = time.perf_counter()
    exception = None
    with indent_log():
        workers = int(os.environ.get("PIP_THREADS", 1))
        with ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="install_given_reqs"
        ) as executor:
            futures = {
                executor.submit(
                    install_requirement,
                    req_name,
                    requirement,
                    global_options,
                    root,
                    home,
                    prefix,
                    warn_script_location,
                    use_user_site,
                    pycompile,
                ): req_name
                for req_name, requirement in to_install.items()
            }
            for future in as_completed(futures):
                req_name = futures[future]
                try:
                    result = future.result()
                    installed.append(InstallationResult(result))
                except Exception as e:
                    logger.error("Installation failed for %s: %s", req_name, str(e))
                    # COMPATIBILITY: cancel_futures was added in python 3.9
                    executor.shutdown(wait=False, cancel_futures=True)
                    exception = e
    end = time.perf_counter()
    print(f"total extraction time: {end-start:.3f}")

    if exception is not None:
        raise exception

    return installed
