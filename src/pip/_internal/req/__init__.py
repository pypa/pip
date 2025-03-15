import collections
import logging
from contextlib import nullcontext
from dataclasses import dataclass
from functools import partial
from typing import Generator, Iterable, List, Optional, Sequence, Tuple
from zipfile import ZipFile

from pip._internal.cli.progress_bars import get_install_progress_renderer
from pip._internal.utils.logging import indent_log
from pip._internal.utils.pyc_compile import WorkerSetting, create_bytecode_compiler

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


def _does_python_size_surpass_threshold(
    requirements: Iterable[InstallRequirement], threshold: int
) -> bool:
    """Inspect wheels to check whether there is enough .py code to
    enable bytecode parallelization.
    """
    py_size = 0
    for req in requirements:
        if not req.local_file_path or not req.is_wheel:
            # No wheel to inspect as this is a legacy editable.
            continue

        with ZipFile(req.local_file_path, allowZip64=True) as wheel_file:
            for entry in wheel_file.infolist():
                if entry.filename.endswith(".py"):
                    py_size += entry.file_size
                    if py_size > threshold:
                        return True

    return False


def install_given_reqs(
    requirements: List[InstallRequirement],
    global_options: Sequence[str],
    root: Optional[str],
    home: Optional[str],
    prefix: Optional[str],
    warn_script_location: bool,
    use_user_site: bool,
    pycompile: bool,
    progress_bar: str,
    workers: WorkerSetting,
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

    show_progress = logger.isEnabledFor(logging.INFO) and len(to_install) > 1

    items = iter(to_install.values())
    if show_progress:
        renderer = get_install_progress_renderer(
            bar_type=progress_bar, total=len(to_install)
        )
        items = renderer(items)

    if pycompile:
        code_size_check = partial(
            _does_python_size_surpass_threshold, to_install.values()
        )
        pycompiler = create_bytecode_compiler(workers, code_size_check)
    else:
        pycompiler = None

    with indent_log(), pycompiler or nullcontext():
        for requirement in items:
            req_name = requirement.name
            assert req_name is not None
            if requirement.should_reinstall:
                logger.info("Attempting uninstall: %s", req_name)
                with indent_log():
                    uninstalled_pathset = requirement.uninstall(auto_confirm=True)
            else:
                uninstalled_pathset = None

            try:
                requirement.install(
                    global_options,
                    root=root,
                    home=home,
                    prefix=prefix,
                    warn_script_location=warn_script_location,
                    use_user_site=use_user_site,
                    pycompiler=pycompiler,
                )
            except Exception:
                # if install did not succeed, rollback previous uninstall
                if uninstalled_pathset and not requirement.install_succeeded:
                    uninstalled_pathset.rollback()
                raise
            else:
                if uninstalled_pathset and requirement.install_succeeded:
                    uninstalled_pathset.commit()

            installed.append(InstallationResult(req_name))

    return installed
