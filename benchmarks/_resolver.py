"""Construct a fresh upstream resolver without timing command setup."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

from pip._internal.commands.install import InstallCommand
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req.constructors import install_req_from_line
from pip._internal.req.req_install import InstallRequirement
from pip._internal.resolution.base import BaseResolver
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.temp_dir import TempDirectory, global_tempdir_manager


@contextmanager
def prepare_resolver(
    wheelhouse: Path,
    requirements: list[str],
    constraints: list[str],
) -> Iterator[tuple[BaseResolver, list[InstallRequirement]]]:
    with ExitStack() as stack:
        stack.enter_context(global_tempdir_manager())
        tracker = stack.enter_context(get_build_tracker())
        build_dir = stack.enter_context(TempDirectory(kind="benchmark-build"))
        session = stack.enter_context(PipSession())
        session.trust_env = False
        command = InstallCommand("install", "benchmark resolver", isolated=True)
        options, _ = command.parse_args(
            [
                "--no-index",
                "--find-links",
                str(wheelhouse),
                "--ignore-installed",
                "--no-cache-dir",
                "--no-build-isolation",
                "--only-binary",
                ":all:",
                "--disable-pip-version-check",
                "--progress-bar",
                "off",
            ]
        )
        finder = command._build_package_finder(options, session)
        preparer = command.make_requirement_preparer(
            build_dir,
            options,
            tracker,
            session,
            finder,
            allow_editables=False,
            use_user_site=False,
        )
        resolver = command.make_resolver(
            preparer, finder, options, ignore_installed=True
        )
        get_requirement.cache_clear()
        reqs = [install_req_from_line(line, isolated=True) for line in requirements]
        reqs.extend(
            install_req_from_line(line, isolated=True, constraint=True)
            for line in constraints
        )
        yield resolver, reqs
