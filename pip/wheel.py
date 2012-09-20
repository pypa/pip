"""
Support installing the "wheel" binary package format.
"""

import os
import sys
import shutil

from pip.util import make_path_relative

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
            if not firstline.startswith('#!python'):
                return False
            firstline = '#!' + sys.executable + os.linesep
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
    import csv
    from pip.backwardcompat import get_path

    if get_path('purelib') != get_path('platlib'):
        # XXX check *.dist-info/WHEEL to deal with this obscurity
        raise NotImplemented("purelib != platlib")

    info_dir = []
    data_dirs = []                
    source = wheeldir.rstrip(os.path.sep) + os.path.sep
    location = dest = get_path('platlib')
    installed = {}
    
    def normpath(src, p):
        return make_path_relative(src, p).replace(os.path.sep, '/')
    
    def record_installed(srcfile, destfile):
        """Map archive RECORD paths to installation RECORD paths."""
        oldpath = normpath(srcfile, wheeldir)
        newpath = normpath(destfile, location)
        installed[oldpath] = newpath
                                
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
                if fixer:
                    fixer(destfile)
                record_installed(srcfile, destfile)

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
                writer.writerow(row)
            for f in installed:
                writer.writerow((installed[f], '', '')) 
    shutil.move(temp_record, record)
                