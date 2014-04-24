"""
This code was taken from https://github.com/ActiveState/appdirs and modified
to suite our purposes.
"""
import os
import sys

from pip._vendor import six


def user_cache_dir(appname):
    r"""
    Return full path to the user-specific cache dir for this application.

        "appname" is the name of application.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Caches/<AppName>
        Unix:       ~/.cache/<AppName> (XDG default)
        Windows:      C:\Users\<username>\AppData\Local\<AppName>\Cache

    On Windows the only suggestion in the MSDN docs is that local settings go
    in the `CSIDL_LOCAL_APPDATA` directory. This is identical to the
    non-roaming app data dir (the default returned by `user_data_dir`). Apps
    typically put cache data somewhere *under* the given dir here. Some
    examples:
        ...\Mozilla\Firefox\Profiles\<ProfileName>\Cache
        ...\Acme\SuperApp\Cache\1.0

    OPINION: This function appends "Cache" to the `CSIDL_LOCAL_APPDATA` value.
    """
    if sys.platform == "win32":
        # Get the base path
        path = os.path.normpath(_get_win_folder("CSIDL_LOCAL_APPDATA"))

        # Add our app name and Cache directory to it
        path = os.path.join(path, appname, "Cache")
    elif sys.platform == "darwin":
        # Get the base path
        path = os.path.expanduser("~/Library/Caches")

        # Add our app name to it
        path = os.path.join(path, appname)
    else:
        # Get the base path
        path = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))

        # Add our app name to it
        path = os.path.join(path, appname)

    return path


# -- Windows support functions --

def _get_win_folder_from_registry(csidl_name):
    """
    This is a fallback technique at best. I'm not sure if using the
    registry for this guarantees us the correct answer for all CSIDL_*
    names.
    """
    import _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(
        _winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    )
    directory, _type = _winreg.QueryValueEx(key, shell_folder_name)
    return directory


def _get_win_folder_with_pywin32(csidl_name):
    from win32com.shell import shellcon, shell
    directory = shell.SHGetFolderPath(0, getattr(shellcon, csidl_name), 0, 0)
    # Try to make this a unicode path because SHGetFolderPath does
    # not return unicode strings when there is unicode data in the
    # path.
    try:
        directory = six.text_type(directory)

        # Downgrade to short path name if have highbit chars. See
        # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
        has_high_char = False
        for c in directory:
            if ord(c) > 255:
                has_high_char = True
                break
        if has_high_char:
            try:
                import win32api
                directory = win32api.GetShortPathName(directory)
            except ImportError:
                pass
    except UnicodeError:
        pass
    return directory


def _get_win_folder_with_ctypes(csidl_name):
    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value

if sys.platform == "win32":
    try:
        import win32com.shell  # noqa
        _get_win_folder = _get_win_folder_with_pywin32
    except ImportError:
        try:
            import ctypes
            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            _get_win_folder = _get_win_folder_from_registry
