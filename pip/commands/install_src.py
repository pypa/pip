"""
Install package as cloned from repos or fallback to regular pip installation

    $ pis install-src requesets

produces dir with cloned request package and its requirements.
"""


from __future__ import absolute_import

import logging
import operator
import os
import tempfile
import shutil
import warnings
try:
    import wheel
except ImportError:
    wheel = None

from pip.req import RequirementSet
from pip.basecommand import RequirementCommand
from pip.locations import virtualenv_no_global, distutils_scheme
from pip.exceptions import (
    InstallationError, CommandError, PreviousBuildDirError,
)
from pip import cmdoptions
from pip.utils import ensure_dir
from pip.utils.build import BuildDirectory
from pip.utils.deprecation import RemovedInPip10Warning
from pip.utils.filesystem import check_path_owner
from pip.wheel import WheelCache, WheelBuilder


logger = logging.getLogger(__name__)






import ast
import contextlib
import os
@contextlib.contextmanager
def working_directory(path):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


#TODO:: write tests
#TODO:: merge with `install` command?
#TODO:: mergable code quality
#TODO:: respect versions by tags or branches
#TODO:: py2 py3
from pip._vendor import requests
from html.parser import HTMLParser
import re
def is_vcs_link(url):
    return re.findall(r'(github.com|bitbucket.org)', url)

class MyHTMLParser(HTMLParser):
    def feed(self, data):
        self.anchor_list = []
        return super().feed(data)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    if is_vcs_link(value):
                        #TODO:: good vcs matcher
                        self.anchor_list.append(value)

parser = MyHTMLParser()

def url2vcses(url):
    from urllib.parse import urlparse
    vcses = []
    parsed = urlparse(url)
    config = {
        #TODO:: comes from config?
        'github.com': ['git'],
        'bitbucket.org': ['git', 'hg'],
    }
    from pip.vcs import vcs
    vcs_names = config.get(parsed.netloc, [])
    for name in vcs_names:
        for registered_vcs in vcs.backends:
            if registered_vcs.name == name:
                vcses.append(registered_vcs)
    return vcses

import ast
class FuncLister(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pkg_name = None
    def visit_Call(self, node):
        if getattr(node.func, 'id', '') == 'setup':
            for keyword in node.keywords:
                if keyword.arg == 'name':
                    self.pkg_name = keyword.value.s
                    return keyword.value.s
        self.generic_visit(node)


def clone_repo(url):
    vcses = url2vcses(url)
    import pip
    for vcs_class in vcses:
        vcs = vcs_class(url)
        try:
            vcs.run_command(['clone', url])
        except pip.exceptions.InstallationError as e:
            logger.info('failed cloning: {}'.format(url))
            continue
        else:
            return True
    return False


def source2pkg_name(setuppy_source):
    tree = ast.parse(setuppy_source)
    fl = FuncLister()
    fl.visit(tree)
    return fl.pkg_name

def clone_and_validate(pkg_name, url):
    cloned = clone_repo(url)
    if not cloned:
        return False

    # get setup.py sources
    import glob
    from pip.req.req_install import get_setup_py
    dir_name = max(glob.iglob('*'), key=os.path.getctime)
    setup_py_path = get_setup_py(dir_name,dir_name, dir_name)
    with open(setup_py_path) as f:
        setuppy_source = f.read()

    cloned_pkg_name = source2pkg_name(setuppy_source)
    if pkg_name != cloned_pkg_name.lower():
        import shutil
        shutil.rmtree(dir_name)
        return False
    return True


def get_links_from_pypi(package_name):
    """
    Get all links from `package_name` setup.py.
    """
    links = []
    pypi_url = 'https://pypi.python.org/pypi/{}'.format(package_name)
    response = requests.get(pypi_url)
    parser.feed(response.content.decode('utf8'))
    return parser.anchor_list

def source_install(requirement_set):
    try:
        for pkg_name in requirement_set.requirements.keys()[:]:
            urls = get_links_from_pypi(package_name=pkg_name)
            if not urls:
                continue

            #TODO:: all repos should be checkout to seperate dir, like "pip install flask"
            # mkdir flask (stop when exists?)
            # cd flask
            # git clone flask
            # git clone flask's dependencies
            for url in urls:
                valid = clone_and_validate(pkg_name, url)
                if valid:
                    logger.info("found source: {}".format(url))

                    from pip.req.req_install import get_setup_py
                    from pip.utils import call_subprocess
                    from pip.utils.setuptools_build import SETUPTOOLS_SHIM
                    import sys
                    setup_py = get_setup_py(pkg_name, os.getcwd(), '')
                    call_subprocess( [sys.executable, '-c', SETUPTOOLS_SHIM % setup_py] + ['develop', '--no-deps'], cwd=pkg_name.lower(), show_stdout=False,)
                    del requirement_set.requirements[pkg_name]
                    break
            else:
                logger.info("FAILED source clone for: {} urls: {}".format(pkg_name, urls))
    return requirement_set






class InstallSrcCommand(RequirementCommand):
    """
    Install packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports installing from "requirements files", which provide
    an easy way to specify a whole environment to be installed.
    """
    name = 'install-src'

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Install packages.'

    def __init__(self, *args, **kw):
        super(InstallSrcCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(cmdoptions.constraints())
        cmd_opts.add_option(cmdoptions.editable())
        cmd_opts.add_option(cmdoptions.requirements())
        cmd_opts.add_option(cmdoptions.build_dir())

        cmd_opts.add_option(
            '-t', '--target',
            dest='target_dir',
            metavar='dir',
            default=None,
            help='Install packages into <dir>. '
                 'By default this will not replace existing files/folders in '
                 '<dir>. Use --upgrade to replace existing packages in <dir> '
                 'with new versions.'
        )

        cmd_opts.add_option(
            '-d', '--download', '--download-dir', '--download-directory',
            dest='download_dir',
            metavar='dir',
            default=None,
            help=("Download packages into <dir> instead of installing them, "
                  "regardless of what's already installed."),
        )

        cmd_opts.add_option(cmdoptions.src())

        cmd_opts.add_option(
            '-U', '--upgrade',
            dest='upgrade',
            action='store_true',
            help='Upgrade all specified packages to the newest available '
                 'version. This process is recursive regardless of whether '
                 'a dependency is already satisfied.'
        )

        cmd_opts.add_option(
            '--force-reinstall',
            dest='force_reinstall',
            action='store_true',
            help='When upgrading, reinstall all packages even if they are '
                 'already up-to-date.')

        cmd_opts.add_option(
            '-I', '--ignore-installed',
            dest='ignore_installed',
            action='store_true',
            help='Ignore the installed packages (reinstalling instead).')

        cmd_opts.add_option(cmdoptions.no_deps())

        cmd_opts.add_option(cmdoptions.install_options())
        cmd_opts.add_option(cmdoptions.global_options())

        cmd_opts.add_option(
            '--user',
            dest='use_user_site',
            action='store_true',
            help="Install to the Python user install directory for your "
                 "platform. Typically ~/.local/, or %APPDATA%\Python on "
                 "Windows. (See the Python documentation for site.USER_BASE "
                 "for full details.)")

        cmd_opts.add_option(
            '--egg',
            dest='as_egg',
            action='store_true',
            help="Install packages as eggs, not 'flat', like pip normally "
                 "does. This option is not about installing *from* eggs. "
                 "(WARNING: Because this option overrides pip's normal install"
                 " logic, requirements files may not behave as expected.)")

        cmd_opts.add_option(
            '--root',
            dest='root_path',
            metavar='dir',
            default=None,
            help="Install everything relative to this alternate root "
                 "directory.")

        cmd_opts.add_option(
            '--prefix',
            dest='prefix_path',
            metavar='dir',
            default=None,
            help="Installation prefix where lib, bin and other top-level "
                 "folders are placed")

        cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile py files to pyc",
        )

        cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile py files to pyc",
        )

        cmd_opts.add_option(cmdoptions.use_wheel())
        cmd_opts.add_option(cmdoptions.no_use_wheel())
        cmd_opts.add_option(cmdoptions.no_binary())
        cmd_opts.add_option(cmdoptions.only_binary())
        cmd_opts.add_option(cmdoptions.pre())
        cmd_opts.add_option(cmdoptions.no_clean())
        cmd_opts.add_option(cmdoptions.require_hashes())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        cmdoptions.resolve_wheel_no_use_binary(options)
        cmdoptions.check_install_build_global(options)

        if options.allow_external:
            warnings.warn(
                "--allow-external has been deprecated and will be removed in "
                "the future. Due to changes in the repository protocol, it no "
                "longer has any effect.",
                RemovedInPip10Warning,
            )

        if options.allow_all_external:
            warnings.warn(
                "--allow-all-external has been deprecated and will be removed "
                "in the future. Due to changes in the repository protocol, it "
                "no longer has any effect.",
                RemovedInPip10Warning,
            )

        if options.allow_unverified:
            warnings.warn(
                "--allow-unverified has been deprecated and will be removed "
                "in the future. Due to changes in the repository protocol, it "
                "no longer has any effect.",
                RemovedInPip10Warning,
            )

        if options.download_dir:
            warnings.warn(
                "pip install --download has been deprecated and will be "
                "removed in the future. Pip now has a download command that "
                "should be used instead.",
                RemovedInPip10Warning,
            )
            options.ignore_installed = True

        if options.build_dir:
            options.build_dir = os.path.abspath(options.build_dir)

        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
            if options.prefix_path:
                raise CommandError(
                    "Can not combine '--user' and '--prefix' as they imply "
                    "different installation locations"
                )
            if virtualenv_no_global():
                raise InstallationError(
                    "Can not perform a '--user' install. User site-packages "
                    "are not visible in this virtualenv."
                )
            install_options.append('--user')
            install_options.append('--prefix=')

        temp_target_dir = None
        if options.target_dir:
            options.ignore_installed = True
            temp_target_dir = tempfile.mkdtemp()
            options.target_dir = os.path.abspath(options.target_dir)
            if (os.path.exists(options.target_dir) and not
                    os.path.isdir(options.target_dir)):
                raise CommandError(
                    "Target path exists but is not a directory, will not "
                    "continue."
                )
            install_options.append('--home=' + temp_target_dir)

        global_options = options.global_options or []

        with self._build_session(options) as session:

            finder = self._build_package_finder(options, session)
            build_delete = (not (options.no_clean or options.build_dir))
            wheel_cache = WheelCache(options.cache_dir, options.format_control)
            if options.cache_dir and not check_path_owner(options.cache_dir):
                logger.warning(
                    "The directory '%s' or its parent directory is not owned "
                    "by the current user and caching wheels has been "
                    "disabled. check the permissions and owner of that "
                    "directory. If executing pip with sudo, you may want "
                    "sudo's -H flag.",
                    options.cache_dir,
                )
                options.cache_dir = None

            with BuildDirectory(options.build_dir,
                                delete=build_delete) as build_dir:
                requirement_set = RequirementSet(
                    build_dir=build_dir,
                    src_dir=options.src_dir,
                    download_dir=options.download_dir,
                    upgrade=options.upgrade,
                    as_egg=options.as_egg,
                    ignore_installed=options.ignore_installed,
                    ignore_dependencies=options.ignore_dependencies,
                    force_reinstall=options.force_reinstall,
                    use_user_site=options.use_user_site,
                    target_dir=temp_target_dir,
                    session=session,
                    pycompile=options.compile,
                    isolated=options.isolated_mode,
                    wheel_cache=wheel_cache,
                    require_hashes=options.require_hashes,
                )

                self.populate_requirement_set(
                    requirement_set, args, options, finder, session, self.name,
                    wheel_cache
                )

                if not requirement_set.has_requirements:
                    return

                try:
                    if (options.download_dir or not wheel or not
                            options.cache_dir):
                        # on -d don't do complex things like building
                        # wheels, and don't try to build wheels when wheel is
                        # not installed.
                        requirement_set.prepare_files(finder)
                    else:
                        # build wheels before install.
                        wb = WheelBuilder(
                            requirement_set,
                            finder,
                            build_options=[],
                            global_options=[],
                        )
                        # Ignore the result: a failed wheel will be
                        # installed from the sdist/vcs whatever.
                        wb.build(autobuilding=True)




                    os.mkdir(args[0])
                    with working_directory(args[0]) as cd:
                        requirement_set = source_install(requirement_set)





                    if not options.download_dir:
                        requirement_set.install(
                            install_options,
                            global_options,
                            root=options.root_path,
                            prefix=options.prefix_path,
                        )
                        reqs = sorted(
                            requirement_set.successfully_installed,
                            key=operator.attrgetter('name'))
                        items = []
                        for req in reqs:
                            item = req.name
                            try:
                                if hasattr(req, 'installed_version'):
                                    if req.installed_version:
                                        item += '-' + req.installed_version
                            except Exception:
                                pass
                            items.append(item)
                        installed = ' '.join(items)
                        if installed:
                            logger.info('Successfully installed %s', installed)
                    else:
                        downloaded = ' '.join([
                            req.name
                            for req in requirement_set.successfully_downloaded
                        ])
                        if downloaded:
                            logger.info(
                                'Successfully downloaded %s', downloaded
                            )
                except PreviousBuildDirError:
                    options.no_clean = True
                    raise
                finally:
                    # Clean up
                    if not options.no_clean:
                        requirement_set.cleanup_files()

        if options.target_dir:
            ensure_dir(options.target_dir)

            lib_dir = distutils_scheme('', home=temp_target_dir)['purelib']

            for item in os.listdir(lib_dir):
                target_item_dir = os.path.join(options.target_dir, item)
                if os.path.exists(target_item_dir):
                    if not options.upgrade:
                        logger.warning(
                            'Target directory %s already exists. Specify '
                            '--upgrade to force replacement.',
                            target_item_dir
                        )
                        continue
                    if os.path.islink(target_item_dir):
                        logger.warning(
                            'Target directory %s already exists and is '
                            'a link. Pip will not automatically replace '
                            'links, please remove if replacement is '
                            'desired.',
                            target_item_dir
                        )
                        continue
                    if os.path.isdir(target_item_dir):
                        shutil.rmtree(target_item_dir)
                    else:
                        os.remove(target_item_dir)

                shutil.move(
                    os.path.join(lib_dir, item),
                    target_item_dir
                )
            shutil.rmtree(temp_target_dir)
        return requirement_set
