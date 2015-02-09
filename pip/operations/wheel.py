import logging
import os

from pip.exceptions import CommandError, PreviousBuildDirError
from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet, parse_requirements
from pip.utils.build import BuildDirectory
from pip.wheel import WheelBuilder


logger = logging.getLogger(__name__)


def build_wheel(index_urls, options, args, build_session_func):
    with build_session_func(options) as session:
        finder = PackageFinder(
            find_links=options.find_links,
            index_urls=index_urls,
            use_wheel=options.use_wheel,
            allow_external=options.allow_external,
            allow_unverified=options.allow_unverified,
            allow_all_external=options.allow_all_external,
            allow_all_prereleases=options.pre,
            trusted_hosts=options.trusted_hosts,
            process_dependency_links=options.process_dependency_links,
            session=session,
        )

        build_delete = (not (options.no_clean or options.build_dir))
        with BuildDirectory(options.build_dir,
                            delete=build_delete) as build_dir:
            requirement_set = RequirementSet(
                build_dir=build_dir,
                src_dir=options.src_dir,
                download_dir=None,
                ignore_dependencies=options.ignore_dependencies,
                ignore_installed=True,
                isolated=options.isolated_mode,
                session=session,
                wheel_download_dir=options.wheel_dir
            )

            # make the wheelhouse
            if not os.path.exists(options.wheel_dir):
                os.makedirs(options.wheel_dir)

            # parse args and/or requirements files
            for name in args:
                requirement_set.add_requirement(
                    InstallRequirement.from_line(
                        name, None, isolated=options.isolated_mode,
                    )
                )
            for name in options.editables:
                requirement_set.add_requirement(
                    InstallRequirement.from_editable(
                        name,
                        default_vcs=options.default_vcs,
                        isolated=options.isolated_mode,
                    )
                )
            for filename in options.requirements:
                for req in parse_requirements(
                        filename,
                        finder=finder,
                        options=options,
                        session=session):
                    requirement_set.add_requirement(req)

            # fail if no requirements
            if not requirement_set.has_requirements:
                logger.error(
                    "You must give at least one requirement to %s "
                    "(see \"pip help %s\")",
                    "wheel", "wheel",
                )
                return

            try:
                # build wheels
                wb = WheelBuilder(
                    requirement_set,
                    finder,
                    options.wheel_dir,
                    build_options=options.build_options or [],
                    global_options=options.global_options or [],
                )
                if not wb.build():
                    raise CommandError(
                        "Failed to build one or more wheels"
                    )
            except PreviousBuildDirError:
                options.no_clean = True
                raise
            finally:
                if not options.no_clean:
                    requirement_set.cleanup_files()
