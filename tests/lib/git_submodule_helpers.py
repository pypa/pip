from __future__ import absolute_import

import textwrap


def _create_test_package_submodule(env):
    env.scratch_path.join("version_pkg_submodule").mkdir()
    submodule_path = env.scratch_path / 'version_pkg_submodule'
    env.run('touch', 'testfile', cwd=submodule_path)
    env.run('git', 'init', cwd=submodule_path)
    env.run('git', 'add', '.', cwd=submodule_path)
    env.run('git', 'commit', '-q',
            '--author', 'pip <pypa-dev@googlegroups.com>',
            '-am', 'initial version / submodule', cwd=submodule_path)
    return submodule_path


def _change_test_package_submodule(env, submodule_path):
    submodule_path.join("testfile").write("this is a changed file")
    submodule_path.join("testfile2").write("this is an added file")
    env.run('git', 'add', '.', cwd=submodule_path)
    env.run('git', 'commit', '-q',
            '--author', 'pip <pypa-dev@googlegroups.com>',
            '-am', 'submodule change', cwd=submodule_path)


def _pull_in_submodule_changes_to_module(env, module_path):
    env.run(
        'git',
        'pull',
        '-q',
        'origin',
        'master',
        cwd=module_path / 'testpkg/static/',
    )
    env.run('git', 'commit', '-q',
            '--author', 'pip <pypa-dev@googlegroups.com>',
            '-am', 'submodule change', cwd=module_path)


def _create_test_package_with_submodule(env):
    env.scratch_path.join("version_pkg").mkdir()
    version_pkg_path = env.scratch_path / 'version_pkg'
    version_pkg_path.join("testpkg").mkdir()
    pkg_path = version_pkg_path / 'testpkg'

    pkg_path.join("__init__.py").write("# hello there")
    pkg_path.join("version_pkg.py").write(textwrap.dedent('''\
                                def main():
                                    print('0.1')
                                '''))
    version_pkg_path.join("setup.py").write(textwrap.dedent('''\
                        from setuptools import setup, find_packages
                        setup(name='version_pkg',
                              version='0.1',
                              packages=find_packages(),
                             )
                        '''))
    env.run('git', 'init', cwd=version_pkg_path, expect_error=True)
    env.run('git', 'add', '.', cwd=version_pkg_path, expect_error=True)
    env.run('git', 'commit', '-q',
            '--author', 'pip <pypa-dev@googlegroups.com>',
            '-am', 'initial version', cwd=version_pkg_path,
            expect_error=True)

    submodule_path = _create_test_package_submodule(env)

    env.run(
        'git',
        'submodule',
        'add',
        submodule_path,
        'testpkg/static',
        cwd=version_pkg_path,
        expect_error=True,
    )
    env.run('git', 'commit', '-q',
            '--author', 'pip <pypa-dev@googlegroups.com>',
            '-am', 'initial version w submodule', cwd=version_pkg_path,
            expect_error=True)

    return version_pkg_path, submodule_path
