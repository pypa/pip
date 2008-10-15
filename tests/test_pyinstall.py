#!/usr/bin/env python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import doctest

pyversion = sys.version[:3]
lib_py = 'lib/python%s/' % pyversion
here = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.join(here, 'test-scratch')

from scripttest import TestFileEnvironment

if 'PYTHONPATH' in os.environ:
    del os.environ['PYTHONPATH']

def reset_env():
    global env
    env = TestFileEnvironment(base_path, ignore_hidden=False)
    env.run('virtualenv', '--no-site-packages', env.base_path)
    # To avoid the 0.9c8 svn 1.5 incompatibility:
    env.run('%s/bin/easy_install' % env.base_path, 'http://peak.telecommunity.com/snapshots/setuptools-0.7a1dev-r66388.tar.gz')
    env.run('mkdir', 'src')

def run_pyinstall(*args, **kw):
    import sys
    args = ('python', '../../pyinstall.py', '-E', env.base_path) + args
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

import optparse
parser = optparse.OptionParser(usage='%prog [OPTIONS] [TEST_FILE...]')
parser.add_option('--first', action='store_true',
                  help='Show only first failure')
parser.add_option('--diff', action='store_true',
                  help='Show diffs in doctest failures')
parser.add_option('--show-error', action='store_true',
                  help='Show the errors (use expect_error=True in run_pyinstall)')
parser.add_option('-v', action='store_true',
                  help='Be verbose')

def main():
    global options
    options, args = parser.parse_args()
    reset_env()
    if not args:
        args = ['test_basic.txt', 'test_requirements.txt', 'test_freeze.txt', 'test_proxy.txt']
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
