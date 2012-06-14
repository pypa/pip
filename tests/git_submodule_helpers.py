import textwrap
from tests.test_pip import (mkdir, write_file,)

def _create_test_package_submodule(env):
    mkdir('version_pkg_submodule')
    submodule_path = env.scratch_path/'version_pkg_submodule'
    env.run('touch', 'testfile', cwd=submodule_path)
    env.run('git', 'init', cwd=submodule_path)
    env.run('git', 'add', '.', cwd=submodule_path)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'initial version / submodule', cwd=submodule_path)
    return submodule_path

def _change_test_package_submodule(env, submodule_path):
    write_file(submodule_path/'testfile', 'this is a changed file')
    write_file(submodule_path/'testfile2', 'this is an added file')
    env.run('git', 'add', '.', cwd=submodule_path)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'submodule change', cwd=submodule_path)

def _pull_in_submodule_changes_to_module(env, module_path):
    env.run(*('git submodule foreach git pull -q origin master'.split(' ')), cwd=module_path) # this only exists in git > 1.7.3
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'submodule change', cwd=module_path)

def _create_test_package_with_submodule(env):
    mkdir('version_pkg')
    version_pkg_path = env.scratch_path/'version_pkg'
    mkdir(version_pkg_path/'testpkg')
    pkg_path = version_pkg_path/'testpkg'

    write_file('__init__.py', '# hello there', pkg_path)
    write_file('version_pkg.py', textwrap.dedent('''\
                                def main():
                                    print('0.1')
                                '''), pkg_path)
    write_file('setup.py', textwrap.dedent('''\
                        from setuptools import setup, find_packages
                        setup(name='version_pkg',
                              version='0.1',
                              packages=find_packages(),
                             )
                        '''), version_pkg_path)
    env.run('git', 'init', cwd=version_pkg_path)
    env.run('git', 'add', '.', cwd=version_pkg_path)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'initial version', cwd=version_pkg_path)


    submodule_path = _create_test_package_submodule(env)

    env.run('git', 'submodule', 'add', submodule_path, 'testpkg/static', cwd=version_pkg_path)
    env.run('git', 'commit', '-q',
            '--author', 'Pip <python-virtualenv@googlegroups.com>',
            '-am', 'initial version w submodule', cwd=version_pkg_path)


    return version_pkg_path, submodule_path
