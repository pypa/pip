import os
import sys
from textwrap import dedent
from typing import Optional

import pytest

from pip._internal.build_env import BuildEnvironment, _get_system_sitepackages

from tests.lib import (
    PipTestEnvironment,
    TestPipResult,
    create_basic_wheel_for_package,
    make_test_finder,
)


def indent(text: str, prefix: str) -> str:
    return "\n".join((prefix if line else "") + line for line in text.split("\n"))


def run_with_build_env(
    script: PipTestEnvironment,
    setup_script_contents: str,
    test_script_contents: Optional[str] = None,
) -> TestPipResult:
    build_env_script = script.scratch_path / "build_env.py"
    scratch_path = str(script.scratch_path)
    build_env_script.write_text(
        dedent(
            f"""
            import subprocess
            import sys

            from pip._internal.build_env import BuildEnvironment
            from pip._internal.index.collector import LinkCollector
            from pip._internal.index.package_finder import PackageFinder
            from pip._internal.models.search_scope import SearchScope
            from pip._internal.models.selection_prefs import (
                SelectionPreferences
            )
            from pip._internal.network.session import PipSession
            from pip._internal.utils.temp_dir import global_tempdir_manager

            link_collector = LinkCollector(
                session=PipSession(),
                search_scope=SearchScope.create([{scratch_path!r}], [], False),
            )
            selection_prefs = SelectionPreferences(
                allow_yanked=True,
            )
            finder = PackageFinder.create(
                link_collector=link_collector,
                selection_prefs=selection_prefs,
            )

            with global_tempdir_manager():
                build_env = BuildEnvironment()
            """
        )
        + indent(dedent(setup_script_contents), "    ")
        + indent(
            dedent(
                """
                if len(sys.argv) > 1:
                    with build_env:
                        subprocess.check_call((sys.executable, sys.argv[1]))
                """
            ),
            "    ",
        )
    )
    args = ["python", os.fspath(build_env_script)]
    if test_script_contents is not None:
        test_script = script.scratch_path / "test.py"
        test_script.write_text(dedent(test_script_contents))
        args.append(os.fspath(test_script))
    return script.run(*args)


def test_build_env_allow_empty_requirements_install() -> None:
    finder = make_test_finder()
    build_env = BuildEnvironment()
    for prefix in ("normal", "overlay"):
        build_env.install_requirements(
            finder, [], prefix, kind="Installing build dependencies"
        )


def test_build_env_allow_only_one_install(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "foo", "1.0")
    create_basic_wheel_for_package(script, "bar", "1.0")
    finder = make_test_finder(find_links=[os.fspath(script.scratch_path)])
    build_env = BuildEnvironment()
    for prefix in ("normal", "overlay"):
        build_env.install_requirements(
            finder, ["foo"], prefix, kind=f"installing foo in {prefix}"
        )
        with pytest.raises(AssertionError):
            build_env.install_requirements(
                finder, ["bar"], prefix, kind=f"installing bar in {prefix}"
            )
        with pytest.raises(AssertionError):
            build_env.install_requirements(
                finder, [], prefix, kind=f"installing in {prefix}"
            )


def test_build_env_requirements_check(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "foo", "2.0")
    create_basic_wheel_for_package(script, "bar", "1.0")
    create_basic_wheel_for_package(script, "bar", "3.0")
    create_basic_wheel_for_package(script, "other", "0.5")

    script.pip_install_local("-f", script.scratch_path, "foo", "bar", "other")

    run_with_build_env(
        script,
        """
        r = build_env.check_requirements(['foo', 'bar', 'other'])
        assert r == (set(), {'foo', 'bar', 'other'}), repr(r)

        r = build_env.check_requirements(['foo>1.0', 'bar==3.0'])
        assert r == (set(), {'foo>1.0', 'bar==3.0'}), repr(r)

        r = build_env.check_requirements(['foo>3.0', 'bar>=2.5'])
        assert r == (set(), {'foo>3.0', 'bar>=2.5'}), repr(r)
        """,
    )

    run_with_build_env(
        script,
        """
        build_env.install_requirements(finder, ['foo', 'bar==3.0'], 'normal',
                                       kind='installing foo in normal')

        r = build_env.check_requirements(['foo', 'bar', 'other'])
        assert r == (set(), {'other'}), repr(r)

        r = build_env.check_requirements(['foo>1.0', 'bar==3.0'])
        assert r == (set(), set()), repr(r)

        r = build_env.check_requirements(['foo>3.0', 'bar>=2.5'])
        assert r == ({('foo==2.0', 'foo>3.0')}, set()), repr(r)
        """,
    )

    run_with_build_env(
        script,
        """
        build_env.install_requirements(finder, ['foo', 'bar==3.0'], 'normal',
                                       kind='installing foo in normal')
        build_env.install_requirements(finder, ['bar==1.0'], 'overlay',
                                       kind='installing foo in overlay')

        r = build_env.check_requirements(['foo', 'bar', 'other'])
        assert r == (set(), {'other'}), repr(r)

        r = build_env.check_requirements(['foo>1.0', 'bar==3.0'])
        assert r == ({('bar==1.0', 'bar==3.0')}, set()), repr(r)

        r = build_env.check_requirements(['foo>3.0', 'bar>=2.5'])
        assert r == ({('bar==1.0', 'bar>=2.5'), ('foo==2.0', 'foo>3.0')}, \
            set()), repr(r)
        """,
    )

    run_with_build_env(
        script,
        """
        build_env.install_requirements(
            finder,
            ["bar==3.0"],
            "normal",
            kind="installing bar in normal",
        )
        r = build_env.check_requirements(
            [
                "bar==2.0; python_version < '3.0'",
                "bar==3.0; python_version >= '3.0'",
                "foo==4.0; extra == 'dev'",
            ],
        )
        assert r == (set(), set()), repr(r)
        """,
    )


def test_build_env_overlay_prefix_has_priority(script: PipTestEnvironment) -> None:
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "4.3")
    result = run_with_build_env(
        script,
        """
        build_env.install_requirements(finder, ['pkg==2.0'], 'overlay',
                                       kind='installing pkg==2.0 in overlay')
        build_env.install_requirements(finder, ['pkg==4.3'], 'normal',
                                       kind='installing pkg==4.3 in normal')
        """,
        """
        print(__import__('pkg').__version__)
        """,
    )
    assert result.stdout.strip() == "2.0", str(result)


if sys.version_info < (3, 12):
    BUILD_ENV_ERROR_DEBUG_CODE = r"""
            from distutils.sysconfig import get_python_lib
            print(
                f'imported `pkg` from `{pkg.__file__}`',
                file=sys.stderr)
            print('system sites:\n  ' + '\n  '.join(sorted({
                            get_python_lib(plat_specific=0),
                            get_python_lib(plat_specific=1),
                    })), file=sys.stderr)
    """
else:
    BUILD_ENV_ERROR_DEBUG_CODE = r"""
            from sysconfig import get_paths
            paths = get_paths()
            print(
                f'imported `pkg` from `{pkg.__file__}`',
                file=sys.stderr)
            print('system sites:\n  ' + '\n  '.join(sorted({
                            paths['platlib'],
                            paths['purelib'],
                    })), file=sys.stderr)
    """


@pytest.mark.usefixtures("enable_user_site")
def test_build_env_isolation(script: PipTestEnvironment) -> None:
    # Create dummy `pkg` wheel.
    pkg_whl = create_basic_wheel_for_package(script, "pkg", "1.0")

    # Install it to site packages.
    script.pip_install_local(pkg_whl)

    # And a copy in the user site.
    script.pip_install_local("--ignore-installed", "--user", pkg_whl)

    # And to another directory available through a .pth file.
    target = script.scratch_path / "pth_install"
    script.pip_install_local("-t", target, pkg_whl)
    (script.site_packages_path / "build_requires.pth").write_text(str(target) + "\n")

    # And finally to yet another directory available through PYTHONPATH.
    target = script.scratch_path / "pypath_install"
    script.pip_install_local("-t", target, pkg_whl)
    script.environ["PYTHONPATH"] = target

    system_sites = _get_system_sitepackages()
    # there should always be something to exclude
    assert system_sites

    run_with_build_env(
        script,
        "",
        f"""
        import sys

        try:
            import pkg
        except ImportError:
            pass
        else:
            {BUILD_ENV_ERROR_DEBUG_CODE}
            print('sys.path:\\n  ' + '\\n  '.join(sys.path), file=sys.stderr)
            sys.exit(1)
        # second check: direct check of exclusion of system site packages
        import os

        normalized_path = [os.path.normcase(path) for path in sys.path]
        for system_path in {system_sites!r}:
            assert system_path not in normalized_path, \
            f"{{system_path}} found in {{normalized_path}}"
        """,
    )
