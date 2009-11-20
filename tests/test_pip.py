#!/usr/bin/env python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import doctest

pyversion = sys.version[:3]
lib_py = 'lib/python%s/' % pyversion
here = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.join(here, 'test-scratch')
download_cache = os.path.join(here, 'test-cache')
if not os.path.exists(download_cache):
    os.makedirs(download_cache)

from scripttest import TestFileEnvironment

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

def reset_env(environ=None):
    global env
    if not environ:
        environ = os.environ.copy()
        environ = clear_environ(environ)
        environ['PIP_DOWNLOAD_CACHE'] = download_cache
    environ['PIP_NO_INPUT'] = '1'
    environ['PYTHONPATH'] = os.path.abspath(os.path.join(__file__, '../../'))
    env = TestFileEnvironment(base_path, ignore_hidden=False, environ=environ)
    env.run(sys.executable, '-m', 'virtualenv', '--no-site-packages', env.base_path)
    # make sure we have current setuptools to avoid svn incompatibilities
    env.run('%s/bin/easy_install' % env.base_path, 'setuptools==0.6c11')
    # Uninstall (kind of) pip, so PYTHONPATH can take effect:
    env.run('%s/bin/easy_install' % env.base_path, '-m', 'pip')
    env.run('mkdir', 'src')

def run_pip(*args, **kw):
    import sys
    args = (sys.executable, '-c', 'import pip; pip.main()', '-E', env.base_path) + args
    #print >> sys.__stdout__, 'running', ' '.join(args)
    if options.show_error:
        kw['expect_error'] = True
    result = env.run(*args, **kw)
    if options.show_error and result.returncode:
        print result
    return result

def write_file(filename, text):
    f = open(os.path.join(base_path, filename), 'w')
    f.write(text)
    f.close()

def get_env():
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
    start_keys = set([k for k in start.keys()
                      if not any([k.startswith(i) for i in ignore])])
    end_keys = set([k for k in end.keys()
                    if not any([k.startswith(i) for i in ignore])])
    deleted = dict([(k, start[k]) for k in start_keys.difference(end_keys)])
    created = dict([(k, end[k]) for k in end_keys.difference(start_keys)])
    updated = {}
    for k in start_keys.intersection(end_keys):
        if (start[k].size != end[k].size):
            updated[k] = end[k]
    return dict(deleted=deleted, created=created, updated=updated)

import optparse
parser = optparse.OptionParser(usage='%prog [OPTIONS] [TEST_FILE...]')
parser.add_option('--first', action='store_true',
                  help='Show only first failure')
parser.add_option('--diff', action='store_true',
                  help='Show diffs in doctest failures')
parser.add_option('--show-error', action='store_true',
                  help='Show the errors (use expect_error=True in run_pip)')
parser.add_option('-v', action='store_true',
                  help='Be verbose')

def main():
    global options
    options, args = parser.parse_args()
    reset_env()
    if not args:
        args = ['test_basic.txt', 'test_requirements.txt', 'test_freeze.txt', 'test_proxy.txt', 'test_uninstall.txt', 'test_upgrade.txt', 'test_config.txt']
    optionflags = doctest.ELLIPSIS
    if options.first:
        optionflags |= doctest.REPORT_ONLY_FIRST_FAILURE
    if options.diff:
        optionflags |= doctest.REPORT_UDIFF
    for filename in args:
        if not filename.endswith('.txt'):
            filename += '.txt'
        if not filename.startswith('test_'):
            filename = 'test_' + filename
        ## FIXME: test for filename existance
        failures, successes = doctest.testfile(filename, optionflags=optionflags)
        if options.first and failures:
            break

if __name__ == '__main__':
    main()
