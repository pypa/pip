import logging
import os
import sys

from importlib import import_module
from sysconfig import get_paths

from pip._vendor import pytoml, six
from pip._internal.utils.misc import call_subprocess, ensure_dir
from pip._internal.utils.setuptools_build import SETUPTOOLS_SHIM
from pip._internal.utils.temp_dir import TempDirectory

logger = logging.getLogger(__name__)


class BuildEnvironment(object):
    """Context manager to install build deps in a simple temporary environment
    """

    def __init__(self, no_clean):
        # TODO: Reuse build environment objects in the installation set
        self._temp_dir = TempDirectory(kind="build-env")
        self._no_clean = no_clean
        self._temp_dir_created = False

    def cleanup(self):
        return self._temp_dir.cleanup()

    def __enter__(self):
        if not self._temp_dir_created:
            self._temp_dir.create()
            self._temp_dir_created = True

        self.save_path = os.environ.get('PATH', None)
        self.save_pythonpath = os.environ.get('PYTHONPATH', None)

        install_scheme = 'nt' if (os.name == 'nt') else 'posix_prefix'
        install_dirs = get_paths(install_scheme, vars={
            'base': self._temp_dir.path,
            'platbase': self._temp_dir.path,
        })

        scripts = install_dirs['scripts']
        if self.save_path:
            os.environ['PATH'] = scripts + os.pathsep + self.save_path
        else:
            os.environ['PATH'] = scripts + os.pathsep + os.defpath

        if install_dirs['purelib'] == install_dirs['platlib']:
            lib_dirs = install_dirs['purelib']
        else:
            lib_dirs = install_dirs['purelib'] + os.pathsep + \
                install_dirs['platlib']
        if self.save_pythonpath:
            os.environ['PYTHONPATH'] = lib_dirs + os.pathsep + \
                self.save_pythonpath
        else:
            os.environ['PYTHONPATH'] = lib_dirs

        return self._temp_dir.path

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._no_clean:
            self._temp_dir.cleanup()
        if self.save_path is None:
            os.environ.pop('PATH', None)
        else:
            os.environ['PATH'] = self.save_path

        if self.save_pythonpath is None:
            os.environ.pop('PYTHONPATH', None)
        else:
            os.environ['PYTHONPATH'] = self.save_pythonpath


class BuildBackend(object):
    """
    PEP 517 Build Backend

    Controls all setup.py interactions
    """

    def __init__(self, setup_py_dir, editable=False):
        self.setup_py_dir = setup_py_dir
        self.editable = editable

    @property
    def setup_py(self):
        return os.path.join(self.setup_py_dir, 'setup.py')

    @property
    def pyproject_toml(self):
        pp_toml = os.path.join(self.setup_py_dir, 'pyproject.toml')

        # Python2 __file__ should not be unicode
        if six.PY2 and isinstance(pp_toml, six.text_type):
            pp_toml = pp_toml.encode(sys.getfilesystemencoding())

        return pp_toml

    def get_requires(self):
        """Obtain the PEP 518 build requirements

        Get a list of the packages required to build the project, if any,
        and a flag indicating whether pyproject.toml is present, indicating
        that the build should be isolated.
        Build requirements can be specified in a pyproject.toml, as described
        in PEP 518. If this file exists but doesn't specify build
        requirements, pip will default to installing setuptools and wheel.
        """
        if os.path.isfile(self.pyproject_toml):
            with open(self.pyproject_toml) as f:
                pp_toml = pytoml.load(f)
            return pp_toml.get('build-system', {})\
                .get('requires', ['setuptools', 'wheel'])

        return ['setuptools', 'wheel']

    def get_requires_for_build_wheel(self):
        """Obtain the PEP 517 build requirements"""
        raise NotImplementedError()

    def prepare_metadata_for_build_wheel(self):
        """Run the setup.py egg_info command"""
        egg_info_cmd = ['egg_info']
        # We can't put the .egg-info files at the root, because then the
        # source code will be mistaken for an installed egg, causing
        # problems
        if self.editable:
            egg_base_option = []
            logger.debug("Preparing metadata for editable distribution")
        else:
            egg_info_dir = os.path.join(self.setup_py_dir, 'pip-egg-info')
            ensure_dir(egg_info_dir)
            egg_base_option = ['--egg-base', 'pip-egg-info']
            logger.debug("Preparing metadata for distribution")

        self._call_setup_py(
            egg_info_cmd + egg_base_option,
            command_desc='python setup.py egg_info')

    def clean(self, global_options=[]):
        self._call_setup_py(list(global_options) + ['clean', '--all'],
                            cwd=self.req_install.source_dir,
                            command_desc='python setup.py clean')

    def build_wheel(self, wheel_directory):
        wheel_args = ['bdist_wheel', '-d', wheel_directory]
        env = {'PYTHONNOUSERSITE': '1'}

        self._call_setup_py(wheel_args,
                            command_desc='python setup.py bdist_wheel',
                            extra_environ=env)

    def _base_setup_args(self):
        flags = '-u'
        # The -S flag currently breaks Python in virtualenvs, because it relies
        # on site.py to find parts of the standard library outside the env. So
        # isolation is disabled for now.
        # if isolate:
        #     flags += 'S'
        return [
            sys.executable, flags, '-c',
            SETUPTOOLS_SHIM % self.setup_py
        ]

    def _call_setup_py(self, args, cwd=None, **kwargs):
        if not cwd:
            cwd = self.setup_py_dir
        logger.debug("setup_py_dir is: " + self.setup_py_dir)
        call_subprocess(self._base_setup_args() + args,
                        cwd=cwd, show_stdout=False, **kwargs)
