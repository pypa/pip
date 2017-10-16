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

    def __init__(self, req_install):
        # The 'pure' OOP way would  be to hold the ONLY reference to
        # self.setup_py_dir and self.setup_py and to implement a method
        # that controls tree changes. I'm not sure how I feel about that
        # now, but we're going to avoid purity in favor of practicality
        # for now, and in fairness, I'm not the only one who created
        # circular dependencies in pip. -xoviat
        self.req_install = req_install
        self.build_environment = BuildEnvironment(no_clean=True)

    @property
    def setup_py(self):
        return self.req_install.setup_py

    @property
    def setup_py_dir(self):
        return self.req_install.setup_py_dir

    @property
    def isolated(self):
        return self.req_install.isolated

    @property
    def editable(self):
        return self.req_install.editable

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
        if self.isolated:
            base_cmd = ["--no-user-cfg"]
        else:
            base_cmd = []
        egg_info_cmd = base_cmd + ['egg_info']
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


class BuildBackendReference(object):
    """
    TMP Class used for quick reference until refactoring (untested)
    """

    def __init__(self, cwd, env, backend_name):
        """
        Entry point for the PEP 517 build backend.

        Returns the value that the build backend returns
        """
        self.cwd = cwd
        self.env = env
        self.backend_name = backend_name

    def __call__(self, backend_function, kwargs):
        """Wrapper for process pool"""
        # Cannot be done in __init__ because would affect main process
        os.chdir(self.cwd)
        os.environ.update(self.env)
        if 'PYTHONPATH' in os.environ:
            sys.path.extend(os.environ['PYTHONPATH'])

        # Import must be deferred until environment is set up
        self.backend = import_module(self.backend_name)

        return getattr(self, backend_function)(**kwargs)

    def get_requires_for_build_wheel(self, config_settings=None):
        if hasattr(self.backend, 'get_requires_for_build_wheel'):
            return self.backend.get_requires_for_build_wheel(config_settings)
        else:
            return ["wheel >= 0.25", "setuptools"]

    def get_requires_for_build_sdist(self, config_settings=None):
        if hasattr(self.backend, 'get_requires_for_build_sdist'):
            return self.backend.get_requires_for_build_sdist(config_settings)
        else:
            return ["setuptools"]

    def prepare_metadata_for_build_wheel(self, output_dir, config_settings):
        """Must create a .dist-info directory containing wheel metadata inside
        the specified metadata_directory (i.e., creates a directory like
        {metadata_directory}/{package}-{version}.dist-info/). This directory
        MUST be a valid .dist-info directory as defined in the wheel
        specification, except that it need not contain RECORD or signatures
        """
        raise NotImplementedError(
            'PEP 517 metadata is currently not implemented')

    def build_sdist(self, sdist_directory, config_settings=None):
        """Must build a .tar.gz source distribution and place it in the specified
        sdist_directory. It must return the basename (not the full path) of the
        .tar.gz file it creates, as a unicode string.
        """
        return self.backend.build_sdist(sdist_directory, config_settings)

    def build_wheel(self, wheel_directory, config_settings=None,
                    build_directory=None, metadata_directory=None):
        """Must build a .whl file, and place it in the specified
        wheel_directory. It must return the basename (not the full
        path) of the .whl file it creates, as a unicode string.

        If the build frontend has previously called
        prepare_metadata_for_build_wheel and depends on the wheel resulting
        from this call to have metadata matching this earlier call, then it
        should provide the path to the created .dist-info directory as the
        metadata_directory argument. If this argument is provided, then
        build_wheel MUST produce a wheel with identical metadata. The
        directory passed in by the build frontend MUST be identical to the
        directory created by prepare_metadata_for_build_wheel, including any
        unrecognized files it created.
        """
        return self.backend.build_wheel(wheel_directory, config_settings,
                                        build_directory, metadata_directory)


class BuildBackendWrapper(object):
    """
    Wraps the build backend in a new subprocess.
    """

    def __init__(self, cwd, env, backend_name='setuptools.pep517'):
        self.cwd = cwd
        self.env = env
        self.backend_name = backend_name
        # self.pool = ProcessPoolExecutor()

    def __getattr__(self, name):
        """Handles aribrary function invokations on the build backend."""

        def method(**kw):
            # return self.pool.submit(
            #     BuildBackend(self.cwd, self.env, self.backend_name),
            #     (name, kw)).result()
            pass

        return method
