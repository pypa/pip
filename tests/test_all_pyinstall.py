import urllib2
import re
import sys
import os
import subprocess
import shutil

pyinstall_fn = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pyinstall.py')

def all_projects():
    data = urllib2.urlopen('http://pypi.python.org/pypi/').read()
    projects = [m.group(1) for m in re.finditer(r'href="/pypi/([^/"]*)', data)]
    return projects

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    if not args:
        print 'Usage: test_all_pyinstall.py <output-dir>'
        sys.exit(1)
    output = args[0]
    if not os.path.exists(output):
        print 'Creating %s' % output
        os.makedirs(output)
    pending_fn = os.path.join(output, 'pending.txt')
    if not os.path.exists(pending_fn):
        print 'Downloading pending list'
        projects = all_projects()
        print 'Found %s projects' % len(projects)
        f = open(pending_fn, 'w')
        for name in projects:
            f.write(name + '\n')
        f.close()
    print 'Starting testing...'
    while os.stat(pending_fn).st_size:
        test_packages(output, pending_fn)
    print 'Finished all pending!'

def test_packages(output, pending_fn):
    package = get_last_item(pending_fn)
    print 'Testing package %s' % package
    dest_dir = os.path.join(output, package)
    print 'Creating virtualenv in %s' % dest_dir
    code = subprocess.call(['virtualenv', dest_dir])
    assert not code, "virtualenv failed"
    print 'Trying installation of %s' % dest_dir
    code = subprocess.call([os.path.join(dest_dir, 'bin', 'python'),
                            pyinstall_fn, package])
    if code:
        print 'Installation of %s failed' % package
        print 'Now checking easy_install...'
        code = subprocess.call([os.path.join(dest_dir, 'bin', 'easy_install'),
                                package])
        if code:
            print 'easy_install also failed'
            add_package(os.path.join(output, 'easy-failure.txt'), package)
        else:
            print 'easy_install succeeded'
            add_package(os.path.join(output, 'failure.txt'), package)
        pop_last_item(pending_fn, package)
    else:
        print 'Installation of %s succeeded' % package
        add_package(os.path.join(output, 'success.txt'), package)
        pop_last_item(pending_fn, package)
        shutil.rmtree(dest_dir)
        
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
