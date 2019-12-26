"""Orchestrator for building wheels from InstallRequirements.
"""

# The following comment should be removed at some point in the future.
# mypy: strict-optional=False

import logging
import os.path
import re
import shutil

from pip._internal.models.link import Link
from pip._internal.utils.logging import indent_log
from pip._internal.utils.marker_files import has_delete_marker_file
from pip._internal.utils.misc import ensure_dir, hash_file
from pip._internal.utils.setuptools_build import (
    make_setuptools_bdist_wheel_args,
    make_setuptools_clean_args,
)
from pip._internal.utils.subprocess import (
    LOG_DIVIDER,
    call_subprocess,
    format_command_args,
    runner_with_spinner_message,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.ui import open_spinner
from pip._internal.utils.unpacking import unpack_file
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import vcs

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Callable, Iterable, List, Optional, Pattern, Text, Tuple,
    )

    from pip._internal.cache import WheelCache
    from pip._internal.operations.prepare import (
        RequirementPreparer
    )
    from pip._internal.req.req_install import InstallRequirement
    from pip._vendor.pep517.wrappers import Pep517HookCaller

    BinaryAllowedPredicate = Callable[[InstallRequirement], bool]

logger = logging.getLogger(__name__)


def _contains_egg_info(
        s, _egg_info_re=re.compile(r'([a-z0-9_.]+)-([a-z0-9_.!+-]+)', re.I)):
    # type: (str, Pattern[str]) -> bool
    """Determine whether the string looks like an egg_info.

    :param s: The string to parse. E.g. foo-2.1
    """
    return bool(_egg_info_re.search(s))


def should_build(
    req,  # type: InstallRequirement
    need_wheel,  # type: bool
    check_binary_allowed,  # type: BinaryAllowedPredicate
):
    # type: (...) -> Optional[bool]
    """Return whether an InstallRequirement should be built into a wheel."""
    if req.constraint:
        # never build requirements that are merely constraints
        return False
    if req.is_wheel:
        if need_wheel:
            logger.info(
                'Skipping %s, due to already being wheel.', req.name,
            )
        return False

    if need_wheel:
        # i.e. pip wheel, not pip install
        return True

    if req.editable or not req.source_dir:
        return False

    if not check_binary_allowed(req):
        logger.info(
            "Skipping wheel build for %s, due to binaries "
            "being disabled for it.", req.name,
        )
        return False

    return True


def should_cache(
    req,  # type: InstallRequirement
    check_binary_allowed,  # type: BinaryAllowedPredicate
):
    # type: (...) -> Optional[bool]
    """
    Return whether a built InstallRequirement can be stored in the persistent
    wheel cache, assuming the wheel cache is available, and should_build()
    has determined a wheel needs to be built.
    """
    if not should_build(
        req, need_wheel=False, check_binary_allowed=check_binary_allowed
    ):
        # never cache if pip install (need_wheel=False) would not have built
        # (editable mode, etc)
        return False

    if req.link and req.link.is_vcs:
        # VCS checkout. Build wheel just for this run
        # unless it points to an immutable commit hash in which
        # case it can be cached.
        assert not req.editable
        assert req.source_dir
        vcs_backend = vcs.get_backend_for_scheme(req.link.scheme)
        assert vcs_backend
        if vcs_backend.is_immutable_rev_checkout(req.link.url, req.source_dir):
            return True
        return False

    link = req.link
    base, ext = link.splitext()
    if _contains_egg_info(base):
        return True

    # Otherwise, build the wheel just for this run using the ephemeral
    # cache since we are either in the case of e.g. a local directory, or
    # no cache directory is available to use.
    return False


def format_command_result(
    command_args,  # type: List[str]
    command_output,  # type: Text
):
    # type: (...) -> str
    """Format command information for logging."""
    command_desc = format_command_args(command_args)
    text = 'Command arguments: {}\n'.format(command_desc)

    if not command_output:
        text += 'Command output: None'
    elif logger.getEffectiveLevel() > logging.DEBUG:
        text += 'Command output: [use --verbose to show]'
    else:
        if not command_output.endswith('\n'):
            command_output += '\n'
        text += 'Command output:\n{}{}'.format(command_output, LOG_DIVIDER)

    return text


def get_legacy_build_wheel_path(
    names,  # type: List[str]
    temp_dir,  # type: str
    name,  # type: str
    command_args,  # type: List[str]
    command_output,  # type: Text
):
    # type: (...) -> Optional[str]
    """Return the path to the wheel in the temporary build directory."""
    # Sort for determinism.
    names = sorted(names)
    if not names:
        msg = (
            'Legacy build of wheel for {!r} created no files.\n'
        ).format(name)
        msg += format_command_result(command_args, command_output)
        logger.warning(msg)
        return None

    if len(names) > 1:
        msg = (
            'Legacy build of wheel for {!r} created more than one file.\n'
            'Filenames (choosing first): {}\n'
        ).format(name, names)
        msg += format_command_result(command_args, command_output)
        logger.warning(msg)

    return os.path.join(temp_dir, names[0])


def _build_wheel_legacy(
    name,  # type: str
    setup_py_path,  # type: str
    source_dir,  # type: str
    global_options,  # type: List[str]
    build_options,  # type: List[str]
    tempd,  # type: str
):
    # type: (...) -> Optional[str]
    """Build one unpacked package using the "legacy" build process.

    Returns path to wheel if successfully built. Otherwise, returns None.
    """
    wheel_args = make_setuptools_bdist_wheel_args(
        setup_py_path,
        global_options=global_options,
        build_options=build_options,
        destination_dir=tempd,
    )

    spin_message = 'Building wheel for %s (setup.py)' % (name,)
    with open_spinner(spin_message) as spinner:
        logger.debug('Destination directory: %s', tempd)

        try:
            output = call_subprocess(
                wheel_args,
                cwd=source_dir,
                spinner=spinner,
            )
        except Exception:
            spinner.finish("error")
            logger.error('Failed building wheel for %s', name)
            return None

        names = os.listdir(tempd)
        wheel_path = get_legacy_build_wheel_path(
            names=names,
            temp_dir=tempd,
            name=name,
            command_args=wheel_args,
            command_output=output,
        )
        return wheel_path


def _build_wheel_pep517(
    name,  # type: str
    backend,  # type: Pep517HookCaller
    metadata_directory,  # type: str
    build_options,  # type: List[str]
    tempd,  # type: str
):
    # type: (...) -> Optional[str]
    """Build one InstallRequirement using the PEP 517 build process.

    Returns path to wheel if successfully built. Otherwise, returns None.
    """
    assert metadata_directory is not None
    if build_options:
        # PEP 517 does not support --build-options
        logger.error('Cannot build wheel for %s using PEP 517 when '
                     '--build-option is present' % (name,))
        return None
    try:
        logger.debug('Destination directory: %s', tempd)

        runner = runner_with_spinner_message(
            'Building wheel for {} (PEP 517)'.format(name)
        )
        with backend.subprocess_runner(runner):
            wheel_name = backend.build_wheel(
                tempd,
                metadata_directory=metadata_directory,
            )
    except Exception:
        logger.error('Failed building wheel for %s', name)
        return None
    return os.path.join(tempd, wheel_name)


def _collect_buildset(
    requirements,  # type: Iterable[InstallRequirement]
    wheel_cache,  # type: WheelCache
    check_binary_allowed,  # type: BinaryAllowedPredicate
    need_wheel,  # type: bool
):
    # type: (...) -> List[Tuple[InstallRequirement, str]]
    """Return the list of InstallRequirement that need to be built,
    with the persistent or temporary cache directory where the built
    wheel needs to be stored.
    """
    buildset = []
    cache_available = bool(wheel_cache.cache_dir)
    for req in requirements:
        if not should_build(
            req,
            need_wheel=need_wheel,
            check_binary_allowed=check_binary_allowed,
        ):
            continue
        if (
            cache_available and
            should_cache(req, check_binary_allowed)
        ):
            cache_dir = wheel_cache.get_path_for_link(req.link)
        else:
            cache_dir = wheel_cache.get_ephem_path_for_link(req.link)
        buildset.append((req, cache_dir))
    return buildset


def _always_true(_):
    # type: (Any) -> bool
    return True


class WheelBuilder(object):
    """Build wheels from a RequirementSet."""

    def __init__(
        self,
        preparer,  # type: RequirementPreparer
        wheel_cache,  # type: WheelCache
        build_options=None,  # type: Optional[List[str]]
        global_options=None,  # type: Optional[List[str]]
        check_binary_allowed=None,  # type: Optional[BinaryAllowedPredicate]
    ):
        # type: (...) -> None
        if check_binary_allowed is None:
            # Binaries allowed by default.
            check_binary_allowed = _always_true

        self.preparer = preparer
        self.wheel_cache = wheel_cache

        self._wheel_dir = preparer.wheel_download_dir

        self.build_options = build_options or []
        self.global_options = global_options or []
        self.check_binary_allowed = check_binary_allowed

    def _build_one(
        self,
        req,  # type: InstallRequirement
        output_dir,  # type: str
    ):
        # type: (...) -> Optional[str]
        """Build one wheel.

        :return: The filename of the built wheel, or None if the build failed.
        """
        try:
            ensure_dir(output_dir)
        except OSError as e:
            logger.warning(
                "Building wheel for %s failed: %s",
                req.name, e,
            )
            return None

        # Install build deps into temporary directory (PEP 518)
        with req.build_env:
            return self._build_one_inside_env(req, output_dir)

    def _build_one_inside_env(
        self,
        req,  # type: InstallRequirement
        output_dir,  # type: str
    ):
        # type: (...) -> Optional[str]
        with TempDirectory(kind="wheel") as temp_dir:
            if req.use_pep517:
                wheel_path = _build_wheel_pep517(
                    name=req.name,
                    backend=req.pep517_backend,
                    metadata_directory=req.metadata_directory,
                    build_options=self.build_options,
                    tempd=temp_dir.path,
                )
            else:
                wheel_path = _build_wheel_legacy(
                    name=req.name,
                    setup_py_path=req.setup_py_path,
                    source_dir=req.unpacked_source_directory,
                    global_options=self.global_options,
                    build_options=self.build_options,
                    tempd=temp_dir.path,
                )

            if wheel_path is not None:
                wheel_name = os.path.basename(wheel_path)
                dest_path = os.path.join(output_dir, wheel_name)
                try:
                    wheel_hash, length = hash_file(wheel_path)
                    shutil.move(wheel_path, dest_path)
                    logger.info('Created wheel for %s: '
                                'filename=%s size=%d sha256=%s',
                                req.name, wheel_name, length,
                                wheel_hash.hexdigest())
                    logger.info('Stored in directory: %s', output_dir)
                    return dest_path
                except Exception as e:
                    logger.warning(
                        "Building wheel for %s failed: %s",
                        req.name, e,
                    )
            # Ignore return, we can't do anything else useful.
            self._clean_one(req)
            return None

    def _clean_one(self, req):
        # type: (InstallRequirement) -> bool
        clean_args = make_setuptools_clean_args(
            req.setup_py_path,
            global_options=self.global_options,
        )

        logger.info('Running setup.py clean for %s', req.name)
        try:
            call_subprocess(clean_args, cwd=req.source_dir)
            return True
        except Exception:
            logger.error('Failed cleaning build dir for %s', req.name)
            return False

    def build(
        self,
        requirements,  # type: Iterable[InstallRequirement]
        should_unpack,  # type: bool
    ):
        # type: (...) -> List[InstallRequirement]
        """Build wheels.

        :param should_unpack: If True, after building the wheel, unpack it
            and replace the sdist with the unpacked version in preparation
            for installation.
        :return: The list of InstallRequirement that failed to build.
        """
        # pip install uses should_unpack=True.
        # pip install never provides a _wheel_dir.
        # pip wheel uses should_unpack=False.
        # pip wheel always provides a _wheel_dir (via the preparer).
        assert (
            (should_unpack and not self._wheel_dir) or
            (not should_unpack and self._wheel_dir)
        )

        buildset = _collect_buildset(
            requirements,
            wheel_cache=self.wheel_cache,
            check_binary_allowed=self.check_binary_allowed,
            need_wheel=not should_unpack,
        )
        if not buildset:
            return []

        # TODO by @pradyunsg
        # Should break up this method into 2 separate methods.

        # Build the wheels.
        logger.info(
            'Building wheels for collected packages: %s',
            ', '.join([req.name for (req, _) in buildset]),
        )

        with indent_log():
            build_success, build_failure = [], []
            for req, cache_dir in buildset:
                wheel_file = self._build_one(req, cache_dir)
                if wheel_file:
                    # Update the link for this.
                    req.link = Link(path_to_url(wheel_file))
                    req.local_file_path = req.link.file_path
                    assert req.link.is_wheel
                    if should_unpack:
                        # XXX: This is mildly duplicative with prepare_files,
                        # but not close enough to pull out to a single common
                        # method.
                        # The code below assumes temporary source dirs -
                        # prevent it doing bad things.
                        if (
                            req.source_dir and
                            not has_delete_marker_file(req.source_dir)
                        ):
                            raise AssertionError(
                                "bad source dir - missing marker")
                        # Delete the source we built the wheel from
                        req.remove_temporary_source()
                        # set the build directory again - name is known from
                        # the work prepare_files did.
                        req.source_dir = req.ensure_build_location(
                            self.preparer.build_dir
                        )
                        # extract the wheel into the dir
                        unpack_file(req.link.file_path, req.source_dir)
                    else:
                        # copy from cache to target directory
                        try:
                            ensure_dir(self._wheel_dir)
                            shutil.copy(wheel_file, self._wheel_dir)
                        except OSError as e:
                            logger.warning(
                                "Building wheel for %s failed: %s",
                                req.name, e,
                            )
                            build_failure.append(req)
                            continue
                    build_success.append(req)
                else:
                    build_failure.append(req)

        # notify success/failure
        if build_success:
            logger.info(
                'Successfully built %s',
                ' '.join([req.name for req in build_success]),
            )
        if build_failure:
            logger.info(
                'Failed to build %s',
                ' '.join([req.name for req in build_failure]),
            )
        # Return a list of requirements that failed to build
        return build_failure
