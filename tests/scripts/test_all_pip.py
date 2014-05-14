import os
import re
import sys
import subprocess
from os.path import dirname, abspath

from pip.compat import urllib
from pip.util import rmtree


src_folder = dirname(dirname(abspath(__file__)))

if sys.platform == 'win32':
    bin_dir = 'Scripts'
else:
    bin_dir = 'bin'


def all_projects():
    data = urllib.urlopen('http://pypi.python.org/simple/').read()
    projects = [m.group(1) for m in re.finditer(r'<a.*?>(.+)</a>', data)]
    return projects


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if not args:
        print('Usage: test_all_pip.py <output-dir>')
        sys.exit(1)
    output = os.path.abspath(args[0])
    if not os.path.exists(output):
        print('Creating %s' % output)
        os.makedirs(output)
    pending_fn = os.path.join(output, 'pending.txt')
    if not os.path.exists(pending_fn):
        print('Downloading pending list')
        projects = all_projects()
        print('Found %s projects' % len(projects))
        f = open(pending_fn, 'w')
        for name in projects:
            f.write(name + '\n')
        f.close()
    print('Starting testing...')
    while os.stat(pending_fn).st_size:
        _test_packages(output, pending_fn)
    print('Finished all pending!')


def _test_packages(output, pending_fn):
    package = get_last_item(pending_fn)
    print('Testing package %s' % package)
    dest_dir = os.path.join(output, package)
    print('Creating virtualenv in %s' % dest_dir)
    create_venv(dest_dir)
    print('Uninstalling actual pip')
    code = subprocess.check_call([
        os.path.join(dest_dir, bin_dir, 'pip'),
        'uninstall',
        '-y',
        'pip',
    ])
    assert not code, 'pip uninstallation failed'
    print('Installing development pip')
    code = subprocess.check_call(
        [
            os.path.join(dest_dir, bin_dir, 'python'),
            'setup.py',
            'install'
        ],
        cwd=src_folder,
    )
    assert not code, 'pip installation failed'
    print('Trying installation of %s' % dest_dir)
    code = subprocess.check_call([
        os.path.join(dest_dir, bin_dir, 'pip'),
        'install',
        package,
    ])
    if code:
        print('Installation of %s failed' % package)
        print('Now checking easy_install...')
        create_venv(dest_dir)
        code = subprocess.check_call([
            os.path.join(dest_dir, bin_dir, 'easy_install'),
            package,
        ])
        if code:
            print('easy_install also failed')
            add_package(os.path.join(output, 'easy-failure.txt'), package)
        else:
            print('easy_install succeeded')
            add_package(os.path.join(output, 'failure.txt'), package)
        pop_last_item(pending_fn, package)
    else:
        print('Installation of %s succeeded' % package)
        add_package(os.path.join(output, 'success.txt'), package)
        pop_last_item(pending_fn, package)
        rmtree(dest_dir)


def create_venv(dest_dir):
    if os.path.exists(dest_dir):
        rmtree(dest_dir)
    print('Creating virtualenv in %s' % dest_dir)
    code = subprocess.check_call([
        'virtualenv',
        '--no-site-packages',
        dest_dir,
    ])
    assert not code, "virtualenv failed"


def get_last_item(fn):
    f = open(fn, 'r')
    lines = f.readlines()
    f.close()
    return lines[-1].strip()


def pop_last_item(fn, line=None):
    f = open(fn, 'r')
    lines = f.readlines()
    f.close()
    if line:
        assert lines[-1].strip() == line.strip()
    lines.pop()
    f = open(fn, 'w')
    f.writelines(lines)
    f.close()


def add_package(filename, package):
    f = open(filename, 'a')
    f.write(package + '\n')
    f.close()


if __name__ == '__main__':
    main()
