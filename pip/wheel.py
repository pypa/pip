"""
Support functions for installing and building the "wheel" binary package format.
"""
from __future__ import with_statement

import csv
import os
import sys
import shutil
import functools
import hashlib
from pip.log import logger
from pip.util import call_subprocess, normalize_path

from base64 import urlsafe_b64encode

from pip.util import make_path_relative

def rehash(path, algo='sha256', blocksize=1<<20):
    """Return (hash, length) for path using hashlib.new(algo)"""
    h = hashlib.new(algo)
    length = 0
    with open(path) as f:
        block = f.read(blocksize)
        while block:
            length += len(block)
            h.update(block)
            block = f.read(blocksize)
    digest = 'sha256='+urlsafe_b64encode(h.digest()).decode('latin1').rstrip('=')
    return (digest, length)

try:
    unicode
    def binary(s):
        if isinstance(s, unicode):
            return s.encode('ascii')
        return s
except NameError:
    def binary(s):
        if isinstance(s, str):
            return s.encode('ascii')

def open_for_csv(name, mode):
    if sys.version_info[0] < 3:
        nl = {}
        bin = 'b'
    else:
        nl = { 'newline': '' }
        bin = ''
    return open(name, mode + bin, **nl)

def fix_script(path):
    """Replace #!python with #!/path/to/python
    Return True if file was changed."""
    # XXX RECORD hashes will need to be updated
    if os.path.isfile(path):
        script = open(path, 'rb')
        try:
            firstline = script.readline()
            if not firstline.startswith(binary('#!python')):
                return False
            exename = sys.executable.encode(sys.getfilesystemencoding())
            firstline = binary('#!') + exename + binary(os.linesep)
            rest = script.read()
        finally:
            script.close()
        script = open(path, 'wb')
        try:
            script.write(firstline)
            script.write(rest)
        finally:
            script.close()
        return True

def move_wheel_files(req, wheeldir):
    from pip.backwardcompat import get_path

    if get_path('purelib') != get_path('platlib'):
        # XXX check *.dist-info/WHEEL to deal with this obscurity
        raise NotImplemented("purelib != platlib")

    info_dir = []
    data_dirs = []
    source = wheeldir.rstrip(os.path.sep) + os.path.sep
    location = dest = get_path('platlib')
    installed = {}
    changed = set()

    def normpath(src, p):
        return make_path_relative(src, p).replace(os.path.sep, '/')

    def record_installed(srcfile, destfile, modified=False):
        """Map archive RECORD paths to installation RECORD paths."""
        oldpath = normpath(srcfile, wheeldir)
        newpath = normpath(destfile, location)
        installed[oldpath] = newpath
        if modified:
            changed.add(destfile)

    def clobber(source, dest, is_base, fixer=None):
        for dir, subdirs, files in os.walk(source):
            basedir = dir[len(source):].lstrip(os.path.sep)
            if is_base and basedir.split(os.path.sep, 1)[0].endswith('.data'):
                continue
            for s in subdirs:
                destsubdir = os.path.join(dest, basedir, s)
                if is_base and basedir == '' and destsubdir.endswith('.data'):
                    data_dirs.append(s)
                    continue
                elif (is_base
                    and s.endswith('.dist-info')
                    # is self.req.project_name case preserving?
                    and s.lower().startswith(req.project_name.replace('-', '_').lower())):
                    assert not info_dir, 'Multiple .dist-info directories'
                    info_dir.append(destsubdir)
                if not os.path.exists(destsubdir):
                    os.makedirs(destsubdir)
            for f in files:
                srcfile = os.path.join(dir, f)
                destfile = os.path.join(dest, basedir, f)
                shutil.move(srcfile, destfile)
                changed = False
                if fixer:
                    changed = fixer(destfile)
                record_installed(srcfile, destfile, changed)

    clobber(source, dest, True)

    assert info_dir, "%s .dist-info directory not found" % req

    for datadir in data_dirs:
        fixer = None
        for subdir in os.listdir(os.path.join(wheeldir, datadir)):
            fixer = None
            if subdir == 'scripts':
                fixer = fix_script
            source = os.path.join(wheeldir, datadir, subdir)
            dest = get_path(subdir)
            clobber(source, dest, False, fixer=fixer)

    record = os.path.join(info_dir[0], 'RECORD')
    temp_record = os.path.join(info_dir[0], 'RECORD.pip')
    with open_for_csv(record, 'r') as record_in:
        with open_for_csv(temp_record, 'w+') as record_out:
            reader = csv.reader(record_in)
            writer = csv.writer(record_out)
            for row in reader:
                row[0] = installed.pop(row[0], row[0])
                if row[0] in changed:
                    row[1], row[2] = rehash(row[0])
                writer.writerow(row)
            for f in installed:
                writer.writerow((installed[f], '', ''))
    shutil.move(temp_record, record)

def _unique(fn):
    @functools.wraps(fn)
    def unique(*args, **kw):
        seen = set()
        for item in fn(*args, **kw):
            if item not in seen:
                seen.add(item)
                yield item
    return unique

@_unique
def uninstallation_paths(dist):
    """
    Yield all the uninstallation paths for dist based on RECORD-without-.pyc

    Yield paths to all the files in RECORD. For each .py file in RECORD, add
    the .pyc in the same directory.

    UninstallPathSet.add() takes care of the __pycache__ .pyc.
    """
    from pip.req import FakeFile # circular import
    r = csv.reader(FakeFile(dist.get_metadata_lines('RECORD')))
    for row in r:
        path = os.path.join(dist.location, row[0])
        yield path
        if path.endswith('.py'):
            dn, fn = os.path.split(path)
            base = fn[:-3]
            path = os.path.join(dn, base+'.pyc')
            yield path



class WheelBuilder(object):
    """Build wheels from a RequirementSet."""

    # should also be ignorable during package finding
    ignore_list = ['distribute','pip','setuptools']

    def __init__(self, requirement_set, finder, wheel_dir, build_options=[], global_options=[]):
        self.requirement_set = requirement_set
        self.finder = finder
        self.wheel_dir = normalize_path(wheel_dir)
        self.build_options = build_options
        self.global_options = global_options

    def _build_one(self, req):
        """Build one wheel."""

        try:
            import wheel
        except ImportError:
            logger.error('The wheel package is required; Failed to build a wheel for %s.' %req.name)
            return False

        base_args = [
            sys.executable, '-c',
            "import setuptools;__file__=%r;"\
            "exec(compile(open(__file__).read().replace('\\r\\n', '\\n'), __file__, 'exec'))" % req.setup_py] + \
            list(self.global_options)

        logger.notify('Running setup.py bdist_wheel for %s' % req.name)
        logger.notify('Destination directory: %s' % self.wheel_dir)
        wheel_args = base_args + ['bdist_wheel', '-d', self.wheel_dir] + self.build_options
        try:
            call_subprocess(wheel_args, cwd=req.source_dir, show_stdout=False)
            return True
        except:
            logger.error('Failed building wheel for %s' % req.name)
            return False

    def build(self):
        """Build wheels."""

        #unpack and constructs req set
        self.requirement_set.prepare_files(self.finder)

        reqset = self.requirement_set.requirements.values()

        #make the wheelhouse
        if not os.path.exists(self.wheel_dir):
            os.makedirs(self.wheel_dir)

        #build the wheels
        logger.notify('Building wheels for collected packages: %s' % ', '.join([req.name for req in reqset]))
        logger.indent += 2
        build_success, build_failure = [], []
        for req in reqset:
            if req.name.lower() in self.ignore_list:
                continue
            if req.is_wheel:
                logger.notify("Skipping existing wheel: %s", req.url)
                continue
            if self._build_one(req):
                build_success.append(req)
            else:
                build_failure.append(req)
        logger.indent -= 2

        #notify sucess/failure
        if build_success:
            logger.notify('Successfully built %s' % ' '.join([req.name for req in build_success]))
        if build_failure:
            logger.notify('Failed to build %s' % ' '.join([req.name for req in build_failure]))
