from __future__ import absolute_import

import compileall
import shutil
import sys
import textwrap

import six
import virtualenv as _virtualenv

from .path import Path

if six.PY3:
    import venv as _venv


class VirtualEnvironment(object):
    """
    An abstraction around virtual environments, currently it only uses
    virtualenv but in the future it could use pyvenv.
    """

    def __init__(self, location, template=None, venv_type=None):
        assert template is None or venv_type is None
        assert venv_type in (None, 'virtualenv', 'venv')
        self.location = Path(location)
        self._venv_type = venv_type or template._venv_type or 'virtualenv'
        self._user_site_packages = False
        self._template = template
        self._sitecustomize = None
        self._update_paths()
        self._create()

    def _update_paths(self):
        home, lib, inc, bin = _virtualenv.path_locations(self.location)
        self.bin = Path(bin)
        self.site = Path(lib) / 'site-packages'
        # Workaround for https://github.com/pypa/virtualenv/issues/306
        if hasattr(sys, "pypy_version_info"):
            version_fmt = '{0}' if six.PY3 else '{0}.{1}'
            version_dir = version_fmt.format(*sys.version_info)
            self.lib = Path(home, 'lib-python', version_dir)
        else:
            self.lib = Path(lib)

    def __repr__(self):
        return "<VirtualEnvironment {}>".format(self.location)

    def _create(self, clear=False):
        if clear:
            shutil.rmtree(self.location)
        if self._template:
            # On Windows, calling `_virtualenv.path_locations(target)`
            # will have created the `target` directory...
            if sys.platform == 'win32' and self.location.exists():
                self.location.rmdir()
            # Clone virtual environment from template.
            shutil.copytree(
                self._template.location, self.location, symlinks=True
            )
            self._sitecustomize = self._template.sitecustomize
            self._user_site_packages = self._template.user_site_packages
        else:
            # Create a new virtual environment.
            if self._venv_type == 'virtualenv':
                _virtualenv.create_environment(
                    self.location,
                    no_pip=True,
                    no_wheel=True,
                    no_setuptools=True,
                )
                self._fix_virtualenv_site_module()
            elif self._venv_type == 'venv':
                builder = _venv.EnvBuilder()
                context = builder.ensure_directories(self.location)
                builder.create_configuration(context)
                builder.setup_python(context)
                self.site.mkdir(parents=True, exist_ok=True)
            self.sitecustomize = self._sitecustomize
            self.user_site_packages = self._user_site_packages

    def _fix_virtualenv_site_module(self):
        # Patch `site.py` so user site work as expected.
        site_py = self.lib / 'site.py'
        with open(site_py) as fp:
            site_contents = fp.read()
        for pattern, replace in (
            (
                # Ensure enabling user site does not result in adding
                # the real site-packages' directory to `sys.path`.
                (
                    '\ndef virtual_addsitepackages(known_paths):\n'
                ),
                (
                    '\ndef virtual_addsitepackages(known_paths):\n'
                    '    return known_paths\n'
                ),
            ),
            (
                # Fix sites ordering: user site must be added before system.
                (
                    '\n    paths_in_sys = addsitepackages(paths_in_sys)'
                    '\n    paths_in_sys = addusersitepackages(paths_in_sys)\n'
                ),
                (
                    '\n    paths_in_sys = addusersitepackages(paths_in_sys)'
                    '\n    paths_in_sys = addsitepackages(paths_in_sys)\n'
                ),
            ),
        ):
            assert pattern in site_contents
            site_contents = site_contents.replace(pattern, replace)
        with open(site_py, 'w') as fp:
            fp.write(site_contents)
        # Make sure bytecode is up-to-date too.
        assert compileall.compile_file(str(site_py), quiet=1, force=True)

    def _customize_site(self):
        contents = ''
        if self._venv_type == 'venv':
            # Enable user site (before system).
            contents += textwrap.dedent(
                '''
                import os, site, sys

                if not os.environ.get('PYTHONNOUSERSITE', False):

                    site.ENABLE_USER_SITE = True

                    # First, drop system-sites related paths.
                    original_sys_path = sys.path[:]
                    known_paths = set()
                    for path in site.getsitepackages():
                        site.addsitedir(path, known_paths=known_paths)
                    system_paths = sys.path[len(original_sys_path):]
                    for path in system_paths:
                        if path in original_sys_path:
                            original_sys_path.remove(path)
                    sys.path = original_sys_path

                    # Second, add user-site.
                    site.addsitedir(site.getusersitepackages())

                    # Third, add back system-sites related paths.
                    for path in site.getsitepackages():
                        site.addsitedir(path)
                ''').strip()
        if self._sitecustomize is not None:
            contents += '\n' + self._sitecustomize
        sitecustomize = self.site / "sitecustomize.py"
        sitecustomize.write_text(contents)
        # Make sure bytecode is up-to-date too.
        assert compileall.compile_file(str(sitecustomize), quiet=1, force=True)

    def clear(self):
        self._create(clear=True)

    def move(self, location):
        shutil.move(self.location, location)
        self.location = Path(location)
        self._update_paths()

    @property
    def sitecustomize(self):
        return self._sitecustomize

    @sitecustomize.setter
    def sitecustomize(self, value):
        self._sitecustomize = value
        self._customize_site()

    @property
    def user_site_packages(self):
        return self._user_site_packages

    @user_site_packages.setter
    def user_site_packages(self, value):
        self._user_site_packages = value
        if self._venv_type == 'virtualenv':
            marker = self.lib / "no-global-site-packages.txt"
            if self._user_site_packages:
                marker.unlink()
            else:
                marker.touch()
        elif self._venv_type == 'venv':
            self._customize_site()
