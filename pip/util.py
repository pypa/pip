import shutil
import os
import posixpath
import stat
import urllib
import re
from pip.backwardcompat import WindowsError

__all__ = ['rmtree', 'display_path', 'backup_dir',
           'find_command', 'splitext', 'ask', 'Inf',
           'url_to_filename', 'filename_to_url',
           'filename_to_url2', 'normalize_name']

def rmtree(dir):
    shutil.rmtree(dir, ignore_errors=True,
                  onerror=rmtree_errorhandler)

def rmtree_errorhandler(func, path, exc_info):
    """On Windows, the files in .svn are read-only, so when rmtree() tries to
    remove them, an exception is thrown.  We catch that here, remove the
    read-only attribute, and hopefully continue without problems."""
    exctype, value = exc_info[:2]
    # lookin for a windows error
    if exctype is not WindowsError or 'Access is denied' not in str(value):
        raise
    # file type should currently be read only
    if ((os.stat(path).st_mode & stat.S_IREAD) != stat.S_IREAD):
        raise
    # convert to read/write
    os.chmod(path, stat.S_IWRITE)
    # use the original function to repeat the operation
    func(path)

def display_path(path):
    """Gives the display value for a given path, making it relative to cwd
    if possible."""
    path = os.path.normcase(os.path.abspath(path))
    if path.startswith(os.getcwd() + os.path.sep):
        path = '.' + path[len(os.getcwd()):]
    return path

def backup_dir(dir, ext='.bak'):
    """Figure out the name of a directory to back up the given dir to
    (adding .bak, .bak2, etc)"""
    n = 1
    extension = ext
    while os.path.exists(dir + extension):
        n += 1
        extension = ext + str(n)
    return dir + extension
    
def splitext(path):
    """Like os.path.splitext, but take off .tar too"""
    base, ext = posixpath.splitext(path)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext

def find_command(cmd, paths=None, pathext=None):
    """Searches the PATH for the given command and returns its path"""
    if paths is None:
        paths = os.environ.get('PATH', []).split(os.pathsep)
    if isinstance(paths, basestring):
        paths = [paths]
    # check if there are funny path extensions for executables, e.g. Windows
    if pathext is None:
        pathext = os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD')
    pathext = [ext for ext in pathext.lower().split(os.pathsep)]
    # don't use extensions if the command ends with one of them
    if os.path.splitext(cmd)[1].lower() in pathext:
        pathext = ['']
    # check if we find the command on PATH
    for path in paths:
        # try without extension first
        cmd_path = os.path.join(path, cmd)
        for ext in pathext:
            # then including the extension
            cmd_path_ext = cmd_path + ext
            if os.path.exists(cmd_path_ext):
                return cmd_path_ext
        if os.path.exists(cmd_path):
            return cmd_path
    return None

def ask(message, options):
    """Ask the message interactively, with the given possible responses"""
    while 1:
        if os.environ.get('PIP_NO_INPUT'):
            raise Exception('No input was expected ($PIP_NO_INPUT set); question: %s' % message)
        response = raw_input(message)
        response = response.strip().lower()
        if response not in options:
            print 'Your response (%r) was not one of the expected responses: %s' % (
                response, ', '.join(options))
        else:
            return response

class _Inf(object):
    """I am bigger than everything!"""
    def __cmp__(self, a):
        if self is a:
            return 0
        return 1
    def __repr__(self):
        return 'Inf'
Inf = _Inf()
del _Inf


def url_to_filename(url):
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    filename = url[len('file:'):].lstrip('/')
    filename = urllib.unquote(filename)
    if _url_drive_re.match(filename):
        filename = filename[0] + ':' + filename[2:]
    else:
        filename = '/' + filename
    return filename

_drive_re = re.compile('^([a-z]):', re.I)
_url_drive_re = re.compile('^([a-z])[:|]', re.I)

def filename_to_url(filename):
    """
    Convert a path to a file: URL.  The path will be made absolute.
    """
    filename = os.path.normcase(os.path.abspath(filename))
    if _drive_re.match(filename):
        filename = filename[0] + '|' + filename[2:]
    url = urllib.quote(filename)
    url = url.replace(os.path.sep, '/')
    url = url.lstrip('/')
    return 'file:///' + url

def filename_to_url2(filename):
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    filename = os.path.normcase(os.path.abspath(filename))
    drive, filename = os.path.splitdrive(filename)
    filepath = filename.split(os.path.sep)
    url = '/'.join([urllib.quote(part) for part in filepath])
    if not drive:
        url = url.lstrip('/')
    return 'file:///' + drive + url

_normalize_re = re.compile(r'[^a-z]', re.I)

def normalize_name(name):
    return _normalize_re.sub('-', name.lower())
