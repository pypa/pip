from textwrap import dedent

import pytest

from pip._internal.build_env import BuildEnvironment
from tests.lib import create_basic_wheel_for_package, make_test_finder


def indent(text, prefix):
    return "\n".join((prefix if line else "") + line for line in text.split("\n"))


def run_with_build_env(script, setup_script_contents, test_script_contents=None):
    build_env_script = script.scratch_path / "build_env.py"
    build_env_script.write_text(
        dedent(
            """
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
                search_scope=SearchScope.create([{scratch!r}], []),
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
            """.format(
                scratch=str(script.scratch_path)
            )
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
    args = ["python", build_env_script]
    if test_script_contents is not None:
        test_script = script.scratch_path / "test.py"
        test_script.write_text(dedent(test_script_contents))
        args.append(test_script)
    return script.run(*args)


def test_build_env_allow_empty_requirements_install():
    build_env = BuildEnvironment()
    for prefix in ("normal", "overlay"):
        build_env.install_requirements(None, [], prefix, None)


def test_build_env_allow_only_one_install(script):
    create_basic_wheel_for_package(script, "foo", "1.0")
    create_basic_wheel_for_package(script, "bar", "1.0")
    finder = make_test_finder(find_links=[script.scratch_path])
    build_env = BuildEnvironment()
    for prefix in ("normal", "overlay"):
        build_env.install_requirements(
            finder, ["foo"], prefix, f"installing foo in {prefix}"
        )
        with pytest.raises(AssertionError):
            build_env.install_requirements(
                finder, ["bar"], prefix, f"installing bar in {prefix}"
            )
        with pytest.raises(AssertionError):
            build_env.install_requirements(
                finder, [], prefix, f"installing in {prefix}"
            )


def test_build_env_requirements_check(script):

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
                                       'installing foo in normal')

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
                                       'installing foo in normal')
        build_env.install_requirements(finder, ['bar==1.0'], 'overlay',
                                       'installing foo in overlay')

        r = build_env.check_requirements(['foo', 'bar', 'other'])
        assert r == (set(), {'other'}), repr(r)

        r = build_env.check_requirements(['foo>1.0', 'bar==3.0'])
        assert r == ({('bar==1.0', 'bar==3.0')}, set()), repr(r)

        r = build_env.check_requirements(['foo>3.0', 'bar>=2.5'])
        assert r == ({('bar==1.0', 'bar>=2.5'), ('foo==2.0', 'foo>3.0')}, \
            set()), repr(r)
        """,
    )


def test_build_env_overlay_prefix_has_priority(script):
    create_basic_wheel_for_package(script, "pkg", "2.0")
    create_basic_wheel_for_package(script, "pkg", "4.3")
    result = run_with_build_env(
        script,
        """
        build_env.install_requirements(finder, ['pkg==2.0'], 'overlay',
                                       'installing pkg==2.0 in overlay')
        build_env.install_requirements(finder, ['pkg==4.3'], 'normal',
                                       'installing pkg==4.3 in normal')
        """,
        """
        print(__import__('pkg').__version__)
        """,
    )
    assert result.stdout.strip() == "2.0", str(result)


@pytest.mark.incompatible_with_test_venv
def test_build_env_isolation(script):

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

    run_with_build_env(
        script,
        "",
        r"""
        from distutils.sysconfig import get_python_lib
        import sys

        try:
            import pkg
        except ImportError:
            pass
        else:
            print(
                f'imported `pkg` from `{pkg.__file__}`',
                file=sys.stderr)
            print('system sites:\n  ' + '\n  '.join(sorted({
                          get_python_lib(plat_specific=0),
                          get_python_lib(plat_specific=1),
                    })), file=sys.stderr)
            print('sys.path:\n  ' + '\n  '.join(sys.path), file=sys.stderr)
            sys.exit(1)
        """,
    )
