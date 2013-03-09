# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import base64
import codecs
import distutils.util
from email import message_from_file
import hashlib
import imp
import logging
import os
import posixpath
import re
import shutil
import sys
import tempfile
import zipfile

import distlib
from . import DistlibException
from .compat import sysconfig, ZipFile, fsdecode, text_type
from .database import DistributionPath, InstalledDistribution
from .scripts import ScriptMaker
from .util import FileOperator, convert_path, CSVReader, CSVWriter


logger = logging.getLogger(__name__)


if hasattr(sys, 'pypy_version_info'):
    IMP_PREFIX = 'pp'
elif sys.platform.startswith('java'):
    IMP_PREFIX = 'jy'
elif sys.platform == 'cli':
    IMP_PREFIX = 'ip'
else:
    IMP_PREFIX = 'cp'

VER_SUFFIX = sysconfig.get_config_var('py_version_nodot')
if not VER_SUFFIX:   # pragma: no cover
    VER_SUFFIX = '%s%s' % sys.version_info[:2]
PYVER = 'py' + VER_SUFFIX
IMPVER = IMP_PREFIX + VER_SUFFIX

ARCH = distutils.util.get_platform().replace('-', '_').replace('.', '_')

ABI = sysconfig.get_config_var('SOABI')
if ABI and ABI.startswith('cpython-'):
    ABI = ABI.replace('cpython-', 'cp')
else:
    ABI = 'none'

FILENAME_RE = re.compile(r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?
-(?P<py>\w+\d+(\.\w+\d+)*)
-(?P<bi>\w+)
-(?P<ar>\w+)
\.whl$
''', re.IGNORECASE | re.VERBOSE)

NAME_VERSION_RE = re.compile(r'''
(?P<nm>[^-]+)
-(?P<vn>\d+[^-]*)
(-(?P<bn>\d+[^-]*))?$
''', re.IGNORECASE | re.VERBOSE)

SHEBANG_RE = re.compile(br'\s*#![^\r\n]*')

if os.sep == '/':
    to_posix = lambda o: o
else:
    to_posix = lambda o: o.replace(os.sep, '/')


def compatible_tags():
    """
    Return (pyver, abi, arch) tuples compatible with this Python.
    """
    versions = [VER_SUFFIX]
    major = VER_SUFFIX[0]
    for minor in range(sys.version_info[1] - 1, - 1, -1):
        versions.append(''.join([major, str(minor)]))

    abis = []
    for suffix, _, _ in imp.get_suffixes():
        if suffix.startswith('.abi'):
            abis.append(suffix.split('.', 2)[1])
    abis.sort()
    if ABI != 'none':
        abis.insert(0, ABI)
    abis.append('none')
    result = []

    # Most specific - our Python version, ABI and arch
    for abi in abis:
        result.append((''.join((IMP_PREFIX, versions[0])), abi, ARCH))

    # where no ABI / arch dependency, but IMP_PREFIX dependency
    for i, version in enumerate(versions):
        result.append((''.join((IMP_PREFIX, version)), 'none', 'any'))
        if i == 0:
            result.append((''.join((IMP_PREFIX, version[0])), 'none', 'any'))

    # no IMP_PREFIX, ABI or arch dependency
    for i, version in enumerate(versions):
        result.append((''.join(('py', version)), 'none', 'any'))
        if i == 0:
            result.append((''.join(('py', version[0])), 'none', 'any'))
    return result

class Wheel(object):
    """
    Class to build and install from Wheel files (PEP 427).
    """

    wheel_version = (1, 0)
    hash_kind = 'sha256'

    def __init__(self, filename=None, sign=False, verify=False):
        """
        Initialise an instance using a (valid) filename.
        """
        self.sign = sign
        self.verify = verify
        self.buildver = ''
        self.pyver = [PYVER]
        self.abi = ['none']
        self.arch = ['any']
        self.dirname = os.getcwd()
        if filename is None:
            self.name = 'dummy'
            self.version = '0.1'
            self._filename = self.filename
        else:
            m = NAME_VERSION_RE.match(filename)
            if m:
                info = m.groupdict('')
                self.name = info['nm']
                self.version = info['vn']
                self.buildver = info['bn']
                self._filename = self.filename
            else:
                dirname, filename = os.path.split(filename)
                m = FILENAME_RE.match(filename)
                if not m:
                    raise DistlibException('Invalid name or '
                                           'filename: %r' % filename)
                if dirname:
                    self.dirname = dirname
                self._filename = filename
                info = m.groupdict('')
                self.name = info['nm']
                self.version = info['vn']
                self.buildver = info['bn']
                self.pyver = info['py'].split('.')
                self.abi = info['bi'].split('.')
                self.arch = info['ar'].split('.')

    @property
    def filename(self):
        """
        Build and return a filename from the various components.
        """
        if self.buildver:
            buildver = '-' + self.buildver
        else:
            buildver = ''
        pyver = '.'.join(self.pyver)
        abi = '.'.join(self.abi)
        arch = '.'.join(self.arch)
        return '%s-%s%s-%s-%s-%s.whl' % (self.name, self.version, buildver,
                                         pyver, abi, arch)

    @property
    def tags(self):
        for pyver in self.pyver:
            for abi in self.abi:
                for arch in self.arch:
                    yield pyver, abi, arch

    def process_shebang(self, data):
        m = SHEBANG_RE.match(data)
        if m:
            data = b'#!python' + data[m.end():]
        else:
            cr = data.find(b'\r')
            lf = data.find(b'\n')
            if cr < 0 or cr > lf:
                term = b'\n'
            else:
                if data[cr:cr + 2] == b'\r\n':
                    term = b'\r\n'
                else:
                    term = b'\r'
            data = b'#!python' + term + data
        return data

    def get_hash(self, data, hash_kind=None):
        if hash_kind is None:
            hash_kind = self.hash_kind
        try:
            hasher = getattr(hashlib, hash_kind)
        except AttributeError:
            raise DistlibException('Unsupported hash algorithm: %r' % hash_kind)
        result = hasher(data).digest()
        result = base64.urlsafe_b64encode(result).rstrip(b'=').decode('ascii')
        return hash_kind, result

    def write_record(self, records, record_path, base):
        with CSVWriter(record_path) as writer:
            for row in records:
                writer.writerow(row)
            p = to_posix(os.path.relpath(record_path, base))
            writer.writerow((p, '', ''))

    def build(self, paths, tags=None):
        """
        Build a wheel from files in specified paths, and use any specified tags
        when determining the name of the wheel.
        """
        if tags is None:
            tags = {}

        libkey = list(filter(lambda o: o in paths, ('purelib', 'platlib')))[0]
        if libkey == 'platlib':
            is_pure = 'false'
            default_pyver = [IMPVER]
            default_abi = [ABI]
            default_arch = [ARCH]
        else:
            is_pure = 'true'
            default_pyver = [PYVER]
            default_abi = ['none']
            default_arch = ['any']

        self.pyver = tags.get('pyver', default_pyver)
        self.abi = tags.get('abi', default_abi)
        self.arch = tags.get('arch', default_arch)

        libdir = paths[libkey]

        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        archive_paths = []

        # First, stuff which is not in site-packages
        for key in ('data', 'headers', 'scripts'):
            if key not in paths:
                continue
            path = paths[key]
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for fn in files:
                        p = fsdecode(os.path.join(root, fn))
                        rp = os.path.relpath(p, path)
                        ap = to_posix(os.path.join(data_dir, key, rp))
                        archive_paths.append((ap, p))
                        if key == 'scripts' and not p.endswith('.exe'):
                            with open(p, 'rb') as f:
                                data = f.read()
                            data = self.process_shebang(data)
                            with open(p, 'wb') as f:
                                f.write(data)

        # Now, stuff which is in site-packages, other than the
        # distinfo stuff.
        path = libdir
        distinfo = None
        for root, dirs, files in os.walk(path):
            if root == path:
                # At the top level only, save distinfo for later
                # and skip it for now
                for i, dn in enumerate(dirs):
                    dn = fsdecode(dn)
                    if dn.endswith('.dist-info'):
                        distinfo = os.path.join(root, dn)
                        del dirs[i]
                        break
                assert distinfo, '.dist-info directory expected, not found'

            for fn in files:
                # comment out next suite to leave .pyc files in
                if fsdecode(fn).endswith(('.pyc', '.pyo')):
                    continue
                p = os.path.join(root, fn)
                rp = to_posix(os.path.relpath(p, path))
                archive_paths.append((rp, p))

        # Now distinfo. Assumed to be flat, i.e. os.listdir is enough.
        files = os.listdir(distinfo)
        for fn in files:
            if fn not in ('RECORD', 'INSTALLER', 'SHARED'):
                p = fsdecode(os.path.join(distinfo, fn))
                ap = to_posix(os.path.join(info_dir, fn))
                archive_paths.append((ap, p))

        wheel_metadata = [
            'Wheel-Version: %d.%d' % self.wheel_version,
            'Generator: distlib %s' % distlib.__version__,
            'Root-Is-Purelib: %s' % is_pure,
        ]
        for pyver, abi, arch in self.tags:
            wheel_metadata.append('Tag: %s-%s-%s' % (pyver, abi, arch))
        p = os.path.join(distinfo, 'WHEEL')
        with open(p, 'w') as f:
            f.write('\n'.join(wheel_metadata))
        ap = to_posix(os.path.join(info_dir, 'WHEEL'))
        archive_paths.append((ap, p))

        # Now, at last, RECORD.
        # Paths in here are archive paths - nothing else makes sense.
        records = []
        hasher = getattr(hashlib, self.hash_kind)
        for ap, p in archive_paths:
            with open(p, 'rb') as f:
                data = f.read()
            digest = '%s=%s' % self.get_hash(data)
            size = os.path.getsize(p)
            records.append((ap, digest, size))

        p = os.path.join(distinfo, 'RECORD')
        self.write_record(records, p, libdir)
        ap = to_posix(os.path.join(info_dir, 'RECORD'))
        archive_paths.append((ap, p))
        # Now, ready to build the zip file
        pathname = os.path.join(self.dirname, self.filename)
        with ZipFile(pathname, 'w', zipfile.ZIP_DEFLATED) as zf:
            for ap, p in archive_paths:
                logger.debug('Wrote %s to %s in wheel', p, ap)
                zf.write(p, ap)
        return pathname

    def install(self, paths, dry_run=False, executable=None, warner=None):
        """
        Install a wheel to the specified paths. If ``executable`` is specified,
        it should be the Unicode absolute path the to the executable written
        into the shebang lines of any scripts installed. If ``warner`` is
        specified, it should be a callable, which will be called with two
        tuples indicating the wheel version of this software and the wheel
        version in the file, if there is a discrepancy in the versions.
        This can be used to issue any warnings to raise any exceptions.
        """
        pathname = os.path.join(self.dirname, self.filename)
        name_ver = '%s-%s' % (self.name, self.version)
        data_dir = '%s.data' % name_ver
        info_dir = '%s.dist-info' % name_ver

        wheel_metadata_name = posixpath.join(info_dir, 'WHEEL')
        record_name = posixpath.join(info_dir, 'RECORD')

        wrapper = codecs.getreader('utf-8')

        with ZipFile(pathname, 'r') as zf:
            with zf.open(wheel_metadata_name) as bwf:
                wf = wrapper(bwf)
                message = message_from_file(wf)
            wv = message['Wheel-Version'].split('.', 1)
            file_version = tuple([int(i) for i in wv])
            if (file_version != self.wheel_version) and warner:
                warner(self.wheel_version, file_version)

            if message['Root-Is-Purelib'] == 'true':
                libdir = paths['purelib']
            else:
                libdir = paths['platlib']
            records = {}
            with zf.open(record_name) as bf:
                wf = wrapper(bf)
                with CSVReader(record_name, stream=wf) as reader:
                    for row in reader:
                        p = row[0]
                        records[p] = row

            data_pfx = posixpath.join(data_dir, '')
            script_pfx = posixpath.join(data_dir, 'scripts', '')

            fileop = FileOperator(dry_run=dry_run)
            fileop.record = True    # so we can rollback if needed

            bc = not sys.dont_write_bytecode    # Double negatives. Lovely!

            outfiles = []   # for RECORD writing

            # for script copying/shebang processing
            workdir = tempfile.mkdtemp()
            # set target dir later
            # we default add_launchers to False, as the
            # Python Launcher should be used instead
            maker = ScriptMaker(workdir, None, fileop=fileop,
                                add_launchers=False)
            maker.executable = executable
            try:
                for zinfo in zf.infolist():
                    arcname = zinfo.filename
                    row = records[arcname]
                    if row[2] and str(zinfo.file_size) != row[2]:
                        raise DistlibException('size mismatch for '
                                               '%s' % arcname)
                    if row[1]:
                        kind, value = row[1].split('=', 1)
                        with zf.open(arcname) as bf:
                            data = bf.read()
                        _, digest = self.get_hash(data, kind)
                        if digest != value:
                            raise DistlibException('digest mismatch for '
                                                   '%s' % arcname)

                    is_script = (arcname.startswith(script_pfx)
                                 and not arcname.endswith('.exe'))

                    if arcname.startswith(data_pfx):
                        _, where, rp = arcname.split('/', 2)
                        outfile = os.path.join(paths[where], convert_path(rp))
                    else:
                        # meant for site-packages.
                        if arcname in (wheel_metadata_name, record_name):
                            continue
                        outfile = os.path.join(libdir, convert_path(arcname))
                    if not is_script:
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, outfile)
                        outfiles.append(outfile)
                        # Double check the digest of the written file
                        if not dry_run and row[1]:
                            with open(outfile, 'rb') as bf:
                                data = bf.read()
                                _, newdigest = self.get_hash(data, kind)
                                if newdigest != digest:
                                    raise DistlibException('digest mismatch '
                                                           'on write for '
                                                           '%s' % outfile)
                        if bc and outfile.endswith('.py'):
                            try:
                                pyc = fileop.byte_compile(outfile)
                                outfiles.append(pyc)
                            except Exception:
                                # Don't give up if byte-compilation fails,
                                # but log it and perhaps warn the user
                                logger.warning('Byte-compilation failed',
                                               exc_info=True)
                    else:
                        fn = os.path.basename(convert_path(arcname))
                        workname = os.path.join(workdir, fn)
                        with zf.open(arcname) as bf:
                            fileop.copy_stream(bf, workname)

                        dn, fn = os.path.split(outfile)
                        maker.target_dir = dn
                        filenames = maker.make(fn)
                        fileop.set_executable_mode(filenames)
                        outfiles.extend(filenames)

                p = os.path.join(libdir, info_dir)
                dist = InstalledDistribution(p)

                # Write SHARED
                paths = dict(paths) # don't change passed in dict
                del paths['purelib']
                del paths['platlib']
                paths['lib'] = libdir
                p = dist.write_shared_locations(paths, dry_run)
                outfiles.append(p)

                # Write RECORD
                dist.write_installed_files(outfiles, paths['prefix'],
                                           dry_run)

            except Exception as e:  # pragma: no cover
                logger.exception('installation failed.')
                fileop.rollback()
                raise
            finally:
                shutil.rmtree(workdir)

COMPATIBLE_TAGS = compatible_tags()

def is_compatible(wheel, tags=None):
    if not isinstance(wheel, Wheel):
        wheel = Wheel(wheel)    # assume it's a filename
    result = False
    if tags is None:
        tags = COMPATIBLE_TAGS
    for ver, abi, arch in tags:
        if ver in wheel.pyver and abi in wheel.abi and arch in wheel.arch:
            result = True
            break
    return result
