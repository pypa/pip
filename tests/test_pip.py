#!/usr/bin/env python
import os, sys, tempfile, shutil, glob, atexit, textwrap

from path import *
from scripttest import TestFileEnvironment

pyversion = sys.version[:3]

# the directory containing all the tests
here = Path(__file__).abspath.folder

# the root of this pip source distribution
src = os.path.dirname(here) 
download_cache = os.path.join(tempfile.mkdtemp(), 'pip-test-cache')

def demand_dirs(path):
    if not os.path.exists(path): 
        os.makedirs(path)
    
demand_dirs(download_cache)

# Tweak the path so we can find up-to-date pip sources
# (http://bitbucket.org/ianb/pip/issue/98)
sys.path = [src] + sys.path

def create_virtualenv(where, distribute=False):
    save_argv = sys.argv
    
    try:
        import virtualenv
        distribute_opt = ['--distribute'] if distribute else []
        sys.argv = ['virtualenv', '--quiet'] + distribute_opt + ['--no-site-packages', '--unzip-setuptools', where]
        virtualenv.main()
    finally: 
        sys.argv = save_argv

    return virtualenv.path_locations(where)

def relpath(root, other):
    """a poor man's os.path.relpath, since we may not have Python 2.6"""
    prefix = root+Path.sep
    assert other.startswith(prefix)
    return Path(other[len(prefix):])

if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']

try:
    any
except NameError:
    def any(seq):
        for item in seq:
            if item:
                return True
        return False

def clear_environ(environ):
    return dict(((k, v) for k, v in environ.iteritems()
                if not k.lower().startswith('pip_')))

def install_setuptools(env):
    easy_install = os.path.join(env.bin_path, 'easy_install')
    version = 'setuptools==0.6c11'
    if sys.platform != 'win32':
        return env.run(easy_install, version)
    
    tempdir = tempfile.mkdtemp()
    try:
        for f in glob.glob(easy_install+'*'):
            shutil.copy2(f, tempdir)
        return env.run(os.path.join(tempdir, 'easy_install'), version)
    finally:
        shutil.rmtree(tempdir)

def reset_env(environ = None):
    global env
    env = TestPipEnvironment(environ)
    
    return env

env = None

class TestFailure(AssertionError):
    """
    
    An "assertion" failed during testing.

    """
    pass


#
# This cleanup routine prevents the __del__ method that cleans up the
# tree of the last TestPipEnvironment from firing after shutil has
# already been unloaded.
#
def _cleanup():
    global env
    del env
    shutil.rmtree(download_cache, ignore_errors=True)

atexit.register(_cleanup)

class TestPipResult(object):

    def __init__(self, impl, verbose=False):
        self._impl = impl
        
        if verbose:
            print self.stdout
            if self.stderr:
                print '======= stderr ========'
                print self.stderr
                print '======================='

    def __getattr__(self, attr):
        return getattr(self._impl,attr)

    if sys.platform == 'win32':
        @property
        def stdout(self):
            return self._impl.stdout.replace('\r\n', '\n')

        @property
        def stderr(self):
            return self._impl.stderr.replace('\r\n', '\n')
            
        def __str__(self):
            return str(self._impl).replace('\r\n','\n')
    else:
        # Python doesn't automatically forward __str__ through __getattr__
        def __str__(self):
            return str(self._impl)

    def assert_installed(self, pkg_name, with_files=[], without_files=[], without_egg_link=False):
        e = self.test_env

        pkg_dir = e.venv/ 'src'/ pkg_name.lower()

        egg_link_path = e.site_packages / pkg_name + '.egg-link'
        if without_egg_link:
            if egg_link_path in self.files_created:
                raise TestFailure, 'unexpected egg link file created: %r\n%s' % (egg_link_path, self)
        else:
            if not egg_link_path in self.files_created:
                raise TestFailure, 'expected egg link file missing: %r\n%s' % (egg_link_path, self)

            egg_link_file = self.files_created[egg_link_path]

            if not (# FIXME: I don't understand why there's a trailing . here
                    egg_link_file.bytes.endswith('.')
                and egg_link_file.bytes[:-1].strip().endswith(pkg_dir)):
                raise TestFailure, textwrap.dedent(u'''\
                Incorrect egg_link file %r
                Expected ending: %r
                ------- Actual contents -------
                %s
                -------------------------------''' % (
                        egg_link_file, 
                        pkg_dir + u'\n.',
                        egg_link_file.bytes))

        pth_file = Path.string(e.site_packages / 'easy-install.pth')

        if (pth_file in self.files_updated) == without_egg_link:
            raise TestFailure, '%r unexpectedly %supdated by install' % (
                pth_file, ('' if without_egg_link else 'not '))

        if (pkg_dir in self.files_created) == (curdir in without_files):
            raise TestFailure, textwrap.dedent('''\
            expected package directory %r %sto be created
            actually created:
            %s
            ''') % (
                Path.string(pkg_dir), 
                ('not ' if curdir in without_files else ''), 
                sorted(self.files_created.keys()))

        for f in with_files:
            if not (pkg_dir/f).normpath in self.files_created:
                raise TestFailure, 'Package directory %r missing expected content %f' % (pkg_dir,f)

        for f in without_files:
            if (pkg_dir/f).normpath in self.files_created:
                raise TestFailure, 'Package directory %r has unexpected content %f' % (pkg_dir,f)

class TestPipEnvironment(TestFileEnvironment):
    """A specialized TestFileEnvironment for testing pip"""

    #
    # Attribute naming convention
    # ---------------------------
    # 
    # Instances of this class have many attributes representing paths
    # in the filesystem.  To keep things straight, absolute paths have
    # a name of the form xxxx_path and relative paths have a name that
    # does not end in '_path'.

    # The following paths are relative to the root_path, and should be
    # treated by clients as instance attributes.  The fact that they
    # are defined in the class is an implementation detail

    # where we'll create the virtual Python installation for testing
    #
    # Named with a leading dot to reduce the chance of spurious
    # results due to being mistaken for the virtualenv package.
    venv = Path('.virtualenv') 

    # The root of a directory tree to be used arbitrarily by tests
    scratch = Path('scratch')

    exe = '.exe' if sys.platform == 'win32' else ''

    verbose = False

    def __init__(self, environ=None):
        
        self.root_path = Path(tempfile.mkdtemp('-piptest'))

        # We will set up a virtual environment at root_path.  
        self.scratch_path = self.root_path / self.scratch

        self.venv_path = self.root_path / self.venv

        if not environ:
            environ = os.environ.copy()
            environ = clear_environ(environ)
            environ['PIP_DOWNLOAD_CACHE'] = str(download_cache)

        environ['PIP_NO_INPUT'] = '1'
        environ['PIP_LOG_FILE'] = str(self.root_path/'pip-log.txt')

        super(TestPipEnvironment,self).__init__(
            self.root_path, ignore_hidden=False, 
            environ=environ, split_cmd=False, start_clear=False,
            cwd=self.scratch_path, capture_temp=True, assert_no_temp=True
            )

        demand_dirs(self.venv_path)
        demand_dirs(self.scratch_path)

        use_distribute = os.environ.get('PIP_TEST_USE_DISTRIBUTE', False)

        # Create a virtualenv and remember where it's putting things.
        virtualenv_paths = create_virtualenv(self.venv_path, distribute=use_distribute)

        assert self.venv_path == virtualenv_paths[0] # sanity check

        for id,path in zip(('venv', 'lib', 'include', 'bin'), virtualenv_paths):
            setattr(self, id+'_path', Path(path))
            setattr(self, id, relpath(self.root_path,path))
            
        assert self.venv == TestPipEnvironment.venv # sanity check

        self.site_packages = self.lib/'site-packages'

        # put the test-scratch virtualenv's bin dir first on the PATH
        self.environ['PATH'] = Path.pathsep.join( (self.bin_path, self.environ['PATH']) )

        # test that test-scratch virtualenv creation produced sensible venv python
        result = self.run('python', '-c', 'import sys; print sys.executable')
        pythonbin = result.stdout.strip()

        if Path(pythonbin).noext != self.bin_path/'python':
            raise RuntimeError(
                "Oops! 'python' in our test environment runs %r" 
                " rather than expected %r" % (pythonbin, self.bin_path/'python'))

        # make sure we have current setuptools to avoid svn incompatibilities
        if not use_distribute:
            install_setuptools(self)

        # Uninstall whatever version of pip came with the virtualenv.
        # Earlier versions of pip were incapable of
        # self-uninstallation on Windows, so we use the one we're testing.
        self.run('python', '-c', 
                 'import sys;sys.path.insert(0, %r);import pip;sys.exit(pip.main());' % os.path.dirname(here), 
                 'uninstall', '-vvv', '-y', 'pip')

        # Install this version instead
        self.run('python', 'setup.py', 'install', cwd=src)

    def run(self, *args, **kw):
        if self.verbose:
            print '>> running', args, kw
        cwd = kw.pop('cwd', None)
        run_from = kw.pop('run_from',None)
        assert not cwd or not run_from, "Don't use run_from; it's going away"
        cwd = Path.string(cwd or run_from or self.cwd)
        assert not isinstance(cwd,Path)
        return TestPipResult( super(TestPipEnvironment,self).run(cwd=cwd,*args,**kw), verbose=self.verbose )

    def __del__(self):
        shutil.rmtree(self.root_path, ignore_errors=True)

def run_pip(*args, **kw):
    return env.run('pip', *args, **kw)

def write_file(filename, text, dest=None):
    """Write a file in the dest (default=env.scratch_path)
    
    """
    env = get_env()
    if dest:
        complete_path = dest/ filename
    else:
        complete_path = env.scratch_path/ filename
    f = open(complete_path, 'w')
    f.write(text)
    f.close()

def mkdir(dirname):
    os.mkdir(os.path.join(get_env().scratch_path, dirname))

def get_env():
    if env is None:
        reset_env()
    return env

# FIXME ScriptTest does something similar, but only within a single
# ProcResult; this generalizes it so states can be compared across
# multiple commands.  Maybe should be rolled into ScriptTest?
def diff_states(start, end, ignore=None):
    """
    Differences two "filesystem states" as represented by dictionaries
    of FoundFile and FoundDir objects.

    Returns a dictionary with following keys:

    ``deleted``
        Dictionary of files/directories found only in the start state.

    ``created``
        Dictionary of files/directories found only in the end state.

    ``updated``
        Dictionary of files whose size has changed (FIXME not entirely
        reliable, but comparing contents is not possible because
        FoundFile.bytes is lazy, and comparing mtime doesn't help if
        we want to know if a file has been returned to its earlier
        state).

    Ignores mtime and other file attributes; only presence/absence and
    size are considered.

    """
    ignore = ignore or []
    def prefix_match(path, prefix):
        if path == prefix: 
            return True
        prefix = prefix.rstrip(os.path.sep) + os.path.sep
        return path.startswith(prefix)
        
    start_keys = set([k for k in start.keys()
                      if not any([prefix_match(k, i) for i in ignore])])
    end_keys = set([k for k in end.keys()
                    if not any([prefix_match(k, i) for i in ignore])])
    deleted = dict([(k, start[k]) for k in start_keys.difference(end_keys)])
    created = dict([(k, end[k]) for k in end_keys.difference(start_keys)])
    updated = {}
    for k in start_keys.intersection(end_keys):
        if (start[k].size != end[k].size):
            updated[k] = end[k]
    return dict(deleted=deleted, created=created, updated=updated)

def assert_all_changes( start_state, end_state, expected_changes ):
    """
    Fails if anything changed that isn't listed in the
    expected_changes.  

    start_state is either a dict mapping paths to
    scripttest.[FoundFile|FoundDir] objects or a TestPipResult whose
    files_before we'll test.  end_state is either a similar dict or a
    TestPipResult whose files_after we'll test.

    Note: listing a directory means anything below
    that directory can be expected to have changed.
    """
    start_files = start_state
    end_files = end_state
    if isinstance(start_state, TestPipResult):
        start_files = start_state.files_before
    if isinstance(end_state, TestPipResult):
        end_files = end_state.files_after

    diff = diff_states( start_files, end_files, ignore=expected_changes )
    if diff.values() != [{},{},{}]:
        import pprint
        raise TestFailure, 'Unexpected changes:\n' + '\n'.join(
            [k + ': ' + ', '.join(v.keys()) for k,v in diff.items()])

    # Don't throw away this potentially useful information
    return diff

if __name__ == '__main__':
    sys.stderr.write("Run pip's tests using nosetests. Requires virtualenv, ScriptTest, and nose.\n")
    sys.exit(1)
