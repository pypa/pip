import os
import textwrap

from glob import iglob

def find_build_meta(prefix_path):
    return next(iglob(prefix_path + '/**/build_meta.py', recursive=True))

def patch_build_meta(prefix_path):
    
    build_meta_path = find_build_meta(prefix_path)
    os.remove(build_meta_path)
    with open(build_meta_path, 'w+') as fp:
        fp.write(textwrap.dedent("""
            import os
            import sys
            import tokenize
            import shutil
            import contextlib

            import setuptools
            import distutils


            class SetupRequirementsError(BaseException):
                def __init__(self, specifiers):
                    self.specifiers = specifiers


            class Distribution(setuptools.dist.Distribution):
                def fetch_build_eggs(self, specifiers):
                    raise SetupRequirementsError(specifiers)

                @classmethod
                @contextlib.contextmanager
                def patch(cls):
                    orig = distutils.core.Distribution
                    distutils.core.Distribution = cls
                    try:
                        yield
                    finally:
                        distutils.core.Distribution = orig


            def _run_setup(setup_script='setup.py'):
                # Note that we can reuse our build directory between calls
                # Correctness comes first, then optimization later
                __file__ = setup_script
                __name__ = '__main__'
                f = getattr(tokenize, 'open', open)(__file__)
                code = f.read().replace('\\r\\n', '\\n')
                f.close()
                exec(compile(code, __file__, 'exec'), locals())


            def _fix_config(config_settings):
                config_settings = config_settings or {}
                config_settings.setdefault('--global-option', [])
                return config_settings


            def _get_build_requires(config_settings):
                config_settings = _fix_config(config_settings)
                requirements = ['setuptools', 'wheel']

                sys.argv = sys.argv[:1] + ['egg_info'] + \
                    config_settings["--global-option"]
                try:
                    with Distribution.patch():
                        _run_setup()
                except SetupRequirementsError as e:
                    requirements += e.specifiers

                return requirements


            def get_requires_for_build_wheel(config_settings=None):
                config_settings = _fix_config(config_settings)
                return _get_build_requires(config_settings)


            def get_requires_for_build_sdist(config_settings=None):
                config_settings = _fix_config(config_settings)
                return _get_build_requires(config_settings)


            def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
                sys.argv = sys.argv[:1] + ['dist_info', '--egg-base', metadata_directory]
                _run_setup()

                dist_infos = [f for f in os.listdir(metadata_directory)
                              if f.endswith('.dist-info')]

                assert len(dist_infos) == 1
                return dist_infos[0]


            def build_wheel(wheel_directory, config_settings=None,
                            metadata_directory=None):
                config_settings = _fix_config(config_settings)
                wheel_directory = os.path.abspath(wheel_directory)
                sys.argv = sys.argv[:1] + ['bdist_wheel'] + \
                    config_settings["--global-option"]
                _run_setup()
                if wheel_directory != 'dist':
                    shutil.rmtree(wheel_directory)
                    shutil.copytree('dist', wheel_directory)

                wheels = [f for f in os.listdir(wheel_directory)
                          if f.endswith('.whl')]

                assert len(wheels) == 1
                return wheels[0]


            def build_sdist(sdist_directory, config_settings=None):
                config_settings = _fix_config(config_settings)
                sdist_directory = os.path.abspath(sdist_directory)
                sys.argv = sys.argv[:1] + ['sdist'] + \
                    config_settings["--global-option"]
                _run_setup()
                if sdist_directory != 'dist':
                    shutil.rmtree(sdist_directory)
                    shutil.copytree('dist', sdist_directory)

                sdists = [f for f in os.listdir(sdist_directory)
                          if f.endswith('.tar.gz')]

                assert len(sdists) == 1
                return sdists[0]
                """))
