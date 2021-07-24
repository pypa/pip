# -*- coding: utf-8 -*-
# Copyright (c) 2005-2010 ActiveState Software Inc.
# Copyright (c) 2013 Eddy Petrișor

"""Utilities for determining application-specific dirs.

See <https://github.com/platformdirs/platformdirs> for details and usage.
"""
# Dev Notes:
# - MSDN on where to store app data files:
#   http://support.microsoft.com/default.aspx?scid=kb;en-us;310294#XSLTH3194121123120121120120
# - Mac OS X: http://developer.apple.com/documentation/MacOSX/Conceptual/BPFileSystem/index.html
# - XDG spec for Un*x: https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html

__version__ = "2.0.2"
__version_info__ = 2, 0, 2


import sys
import os

PY2 = sys.version_info[0] == 2

if not PY2:
    unicode = str

if sys.platform.startswith('java'):
    import platform
    os_name = platform.java_ver()[3][0]
    if os_name.startswith('Windows'): # "Windows XP", "Windows 7", etc.
        system = 'win32'
    elif os_name.startswith('Mac'): # "Mac OS X", etc.
        system = 'darwin'
    else: # "Linux", "SunOS", "FreeBSD", etc.
        # Setting this to "linux2" is not ideal, but only Windows or Mac
        # are actually checked for and the rest of the module expects
        # *sys.platform* style strings.
        system = 'linux2'
else:
    system = sys.platform


# https://docs.python.org/dev/library/sys.html#sys.platform
if system == 'win32':
    try:
        from ctypes import windll
    except ImportError:
        try:
            import com.sun.jna
        except ImportError:
            try:
                if PY2:
                    import _winreg as winreg
                else:
                    import winreg
            except ImportError:
                def _get_win_folder(csidl_name):
                    """Get folder from environment variables."""
                    if csidl_name == 'CSIDL_APPDATA':
                        env_var_name = 'APPDATA'
                    elif csidl_name == 'CSIDL_COMMON_APPDATA':
                        env_var_name = 'ALLUSERSPROFILE'
                    elif csidl_name == 'CSIDL_LOCAL_APPDATA':
                        env_var_name = 'LOCALAPPDATA'
                    else:
                        raise ValueError('Unknown CSIDL name: {}'.format(csidl_name))

                    if env_var_name in os.environ:
                        return os.environ[env_var_name]
                    else:
                        raise ValueError('Unset environment variable: {}'.format(env_var_name))
            else:
                def _get_win_folder(csidl_name):
                    """Get folder from the registry.

                    This is a fallback technique at best. I'm not sure if using the
                    registry for this guarantees us the correct answer for all CSIDL_*
                    names.
                    """
                    if csidl_name == 'CSIDL_APPDATA':
                        shell_folder_name = 'AppData'
                    elif csidl_name == 'CSIDL_COMMON_APPDATA':
                        shell_folder_name = 'Common AppData'
                    elif csidl_name == 'CSIDL_LOCAL_APPDATA':
                        shell_folder_name = 'Local AppData'
                    else:
                        raise ValueError('Unknown CSIDL name: {}'.format(csidl_name))

                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
                    )
                    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
                    return directory
        else:
            def _get_win_folder_with_jna(csidl_name):
                """Get folder with JNA."""
                import array
                from com.sun import jna
                from com.sun.jna.platform import win32

                buf_size = win32.WinDef.MAX_PATH * 2
                buf = array.zeros('c', buf_size)
                shell = win32.Shell32.INSTANCE
                shell.SHGetFolderPath(
                    None, getattr(win32.ShlObj, csidl_name), None, win32.ShlObj.SHGFP_TYPE_CURRENT, buf
                )
                directory = jna.Native.toString(buf.tostring()).rstrip('\0')

                # Downgrade to short path name if have highbit chars. See
                # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
                has_high_char = False
                for c in directory:
                    if ord(c) > 255:
                        has_high_char = True
                        break
                if has_high_char:
                    buf = array.zeros('c', buf_size)
                    kernel = win32.Kernel32.INSTANCE
                    if kernel.GetShortPathName(directory, buf, buf_size):
                        directory = jna.Native.toString(buf.tostring()).rstrip('\0')

                return directory
    else:
        def _get_win_folder(csidl_name):
            """Get folder with ctypes."""
            import ctypes

            if csidl_name == 'CSIDL_APPDATA':
                csidl_const = 26
            elif csidl_name == 'CSIDL_COMMON_APPDATA':
                csidl_const = 35
            elif csidl_name == 'CSIDL_LOCAL_APPDATA':
                csidl_const = 28
            else:
                raise ValueError('Unknown CSIDL name: {}'.format(csidl_name))

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

    def _user_data_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        if appauthor is None:
            appauthor = appname

        const = 'CSIDL_APPDATA' if roaming else 'CSIDL_LOCAL_APPDATA'
        path = os.path.normpath(_get_win_folder(const))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)

            if version:
                path = os.path.join(path, version)

        return path

    def _site_data_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        if appauthor is None:
            appauthor = appname

        path = os.path.normpath(_get_win_folder('CSIDL_COMMON_APPDATA'))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)

            if version:
                path = os.path.join(path, version)

        return path

    def _user_config_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        return _user_data_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)

    def _site_config_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        return _site_data_dir_impl(appname=appname, appauthor=appauthor, version=version)

    def _user_cache_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        if appauthor is None:
            appauthor = appname

        path = os.path.normpath(_get_win_folder('CSIDL_LOCAL_APPDATA'))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)

            if opinion:
                path = os.path.join(path, 'Cache')

            if version:
                path = os.path.join(path, version)

        return path

    def _user_state_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        return _user_data_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)

    def _user_log_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        path = _user_data_dir_impl(appname=appname, appauthor=appauthor, version=version)
        if opinion:
            path = os.path.join(path, 'Logs')

        return path

elif system == 'darwin':

    def _user_data_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        path = os.path.expanduser('~/Library/Application Support/')
        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _site_data_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        path = '/Library/Application Support'
        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _user_config_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        path = os.path.expanduser('~/Library/Preferences/')
        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _site_config_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        path = '/Library/Preferences'
        if appname:
            path = os.path.join(path, appname)

        return path

    def _user_cache_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        path = os.path.expanduser('~/Library/Caches')
        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _user_state_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        return _user_data_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)

    def _user_log_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        path = os.path.expanduser('~/Library/Logs')
        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

else:

    def _user_data_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        if 'XDG_DATA_HOME' in os.environ:
            path = os.environ['XDG_DATA_HOME']
        else:
            path = os.path.expanduser('~/.local/share')

        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _site_data_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        # XDG default for $XDG_DATA_DIRS
        # only first, if multipath is False
        if 'XDG_DATA_DIRS' in os.environ:
            path = os.environ['XDG_DATA_DIRS']
        else:
            path = '/usr/local/share{}/usr/share'.format(os.pathsep)

        pathlist = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if appname:
            if version:
                appname = os.path.join(appname, version)
            pathlist = [os.path.join(x, appname) for x in pathlist]

        if multipath:
            path = os.pathsep.join(pathlist)
        else:
            path = pathlist[0]

        return path

    def _user_config_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        if 'XDG_CONFIG_HOME' in os.environ:
            path = os.environ['XDG_CONFIG_HOME']
        else:
            path = os.path.expanduser('~/.config')

        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _site_config_dir_impl(appname=None, appauthor=None, version=None, multipath=False):
        # XDG default for $XDG_CONFIG_DIRSS (missing or empty)
        # see <https://github.com/pypa/pip/pull/7501#discussion_r360624829>
        # only first, if multipath is False
        path = os.getenv('XDG_CONFIG_DIRS') or '/etc/xdg'

        pathlist = [os.path.expanduser(x.rstrip(os.sep)) for x in path.split(os.pathsep)]
        if appname:
            if version:
                appname = os.path.join(appname, version)
            pathlist = [os.path.join(x, appname) for x in pathlist]

        if multipath:
            path = os.pathsep.join(pathlist)
        else:
            path = pathlist[0]

        return path

    def _user_cache_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        if 'XDG_CACHE_HOME' in os.environ:
            path = os.environ['XDG_CACHE_HOME']
        else:
            path = os.path.expanduser('~/.cache')

        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _user_state_dir_impl(appname=None, appauthor=None, version=None, roaming=False):
        if 'XDG_STATE_HOME' in os.environ:
            path = os.environ['XDG_STATE_HOME']
        else:
            path = os.path.expanduser('~/.local/state')

        if appname:
            path = os.path.join(path, appname)
            if version:
                path = os.path.join(path, version)

        return path

    def _user_log_dir_impl(appname=None, appauthor=None, version=None, opinion=True):
        path = _user_cache_dir_impl(appname=appname, appauthor=appauthor, version=version)
        if opinion:
            path = os.path.join(path, 'log')

        return path


def user_data_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user data directories are:
        Mac OS X:               ~/Library/Application Support/<AppName>
        Unix:                   ~/.local/share/<AppName>    # or in $XDG_DATA_HOME, if defined
        Win XP (not roaming):   C:\Documents and Settings\<username>\Application Data\<AppAuthor>\<AppName>
        Win XP (roaming):       C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>
        Win 7  (not roaming):   C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>
        Win 7  (roaming):       C:\Users\<username>\AppData\Roaming\<AppAuthor>\<AppName>

    For Unix, we follow the XDG spec and support $XDG_DATA_HOME.
    That means, by default "~/.local/share/<AppName>".
    """
    return _user_data_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)


def site_data_dir(appname=None, appauthor=None, version=None, multipath=False):
    r"""Return full path to the user-shared data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "multipath" is an optional parameter only applicable to *nix
            which indicates that the entire list of data dirs should be
            returned. By default, the first item from XDG_DATA_DIRS is
            returned, or '/usr/local/share/<AppName>',
            if XDG_DATA_DIRS is not set

    Typical site data directories are:
        Mac OS X:   /Library/Application Support/<AppName>
        Unix:       /usr/local/share/<AppName> or /usr/share/<AppName>
        Win XP:     C:\Documents and Settings\All Users\Application Data\<AppAuthor>\<AppName>
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)
        Win 7:      C:\ProgramData\<AppAuthor>\<AppName>   # Hidden, but writeable on Win 7.

    For Unix, this is using the $XDG_DATA_DIRS[0] default.

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """
    return _site_data_dir_impl(appname=appname, appauthor=appauthor, version=version, multipath=multipath)


def user_config_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific config dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user config directories are:
        Mac OS X:               ~/Library/Preferences/<AppName>
        Unix:                   ~/.config/<AppName>     # or in $XDG_CONFIG_HOME, if defined
        Win *:                  same as user_data_dir

    For Unix, we follow the XDG spec and support $XDG_CONFIG_HOME.
    That means, by default "~/.config/<AppName>".
    """
    return _user_config_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)


def site_config_dir(appname=None, appauthor=None, version=None, multipath=False):
    r"""Return full path to the user-shared data dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "multipath" is an optional parameter only applicable to *nix
            which indicates that the entire list of config dirs should be
            returned. By default, the first item from XDG_CONFIG_DIRS is
            returned, or '/etc/xdg/<AppName>', if XDG_CONFIG_DIRS is not set

    Typical site config directories are:
        Mac OS X:   same as site_data_dir
        Unix:       /etc/xdg/<AppName> or $XDG_CONFIG_DIRS[i]/<AppName> for each value in
                    $XDG_CONFIG_DIRS
        Win *:      same as site_data_dir
        Vista:      (Fail! "C:\ProgramData" is a hidden *system* directory on Vista.)

    For Unix, this is using the $XDG_CONFIG_DIRS[0] default, if multipath=False

    WARNING: Do not use this on Windows. See the Vista-Fail note above for why.
    """
    return _site_config_dir_impl(appname=appname, appauthor=appauthor, version=version, multipath=multipath)


def user_cache_dir(appname=None, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific cache dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "opinion" (boolean) can be False to disable the appending of
            "Cache" to the base app data dir for Windows. See
            discussion below.

    Typical user cache directories are:
        Mac OS X:   ~/Library/Caches/<AppName>
        Unix:       ~/.cache/<AppName> (XDG default)
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Cache
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Cache

    On Windows the only suggestion in the MSDN docs is that local settings go in
    the `CSIDL_LOCAL_APPDATA` directory. This is identical to the non-roaming
    app data dir (the default returned by `user_data_dir` above). Apps typically
    put cache data somewhere *under* the given dir here. Some examples:
        ...\Mozilla\Firefox\Profiles\<ProfileName>\Cache
        ...\Acme\SuperApp\Cache\1.0
    OPINION: This function appends "Cache" to the `CSIDL_LOCAL_APPDATA` value.
    This can be disabled with the `opinion=False` option.
    """
    return _user_cache_dir_impl(appname=appname, appauthor=appauthor, version=version, opinion=opinion)


def user_state_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""Return full path to the user-specific state dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "roaming" (boolean, default False) can be set True to use the Windows
            roaming appdata directory. That means that for users on a Windows
            network setup for roaming profiles, this user data will be
            sync'd on login. See
            <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>
            for a discussion of issues.

    Typical user state directories are:
        Mac OS X:  same as user_data_dir
        Unix:      ~/.local/state/<AppName>   # or in $XDG_STATE_HOME, if defined
        Win *:     same as user_data_dir

    For Unix, we follow this Debian proposal <https://wiki.debian.org/XDGBaseDirectorySpecification#state>
    to extend the XDG spec and support $XDG_STATE_HOME.

    That means, by default "~/.local/state/<AppName>".
    """
    return _user_state_dir_impl(appname=appname, appauthor=appauthor, version=version, roaming=roaming)


def user_log_dir(appname=None, appauthor=None, version=None, opinion=True):
    r"""Return full path to the user-specific log dir for this application.

        "appname" is the name of application.
            If None, just the system directory is returned.
        "appauthor" (only used on Windows) is the name of the
            appauthor or distributing body for this application. Typically
            it is the owning company name. This falls back to appname. You may
            pass False to disable it.
        "version" is an optional version path element to append to the
            path. You might want to use this if you want multiple versions
            of your app to be able to run independently. If used, this
            would typically be "<major>.<minor>".
            Only applied when appname is present.
        "opinion" (boolean) can be False to disable the appending of
            "Logs" to the base app data dir for Windows, and "log" to the
            base cache dir for Unix. See discussion below.

    Typical user log directories are:
        Mac OS X:   ~/Library/Logs/<AppName>
        Unix:       ~/.cache/<AppName>/log  # or under $XDG_CACHE_HOME if defined
        Win XP:     C:\Documents and Settings\<username>\Local Settings\Application Data\<AppAuthor>\<AppName>\Logs
        Vista:      C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>\Logs

    On Windows the only suggestion in the MSDN docs is that local settings
    go in the `CSIDL_LOCAL_APPDATA` directory. (Note: I'm interested in
    examples of what some windows apps use for a logs dir.)

    OPINION: This function appends "Logs" to the `CSIDL_LOCAL_APPDATA`
    value for Windows and appends "log" to the user cache dir for Unix.
    This can be disabled with the `opinion=False` option.
    """
    return _user_log_dir_impl(appname=appname, appauthor=appauthor, version=version, opinion=opinion)


class PlatformDirs(object):
    """Convenience wrapper for getting application dirs."""
    def __init__(self, appname=None, appauthor=None, version=None,
            roaming=False, multipath=False):
        self.appname = appname
        self.appauthor = appauthor
        self.version = version
        self.roaming = roaming
        self.multipath = multipath

    @property
    def user_data_dir(self):
        return user_data_dir(self.appname, self.appauthor,
                             version=self.version, roaming=self.roaming)

    @property
    def site_data_dir(self):
        return site_data_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)

    @property
    def user_config_dir(self):
        return user_config_dir(self.appname, self.appauthor,
                               version=self.version, roaming=self.roaming)

    @property
    def site_config_dir(self):
        return site_config_dir(self.appname, self.appauthor,
                             version=self.version, multipath=self.multipath)

    @property
    def user_cache_dir(self):
        return user_cache_dir(self.appname, self.appauthor,
                              version=self.version)

    @property
    def user_state_dir(self):
        return user_state_dir(self.appname, self.appauthor,
                              version=self.version)

    @property
    def user_log_dir(self):
        return user_log_dir(self.appname, self.appauthor,
                            version=self.version)


# Backwards compatibility with appdirs
AppDirs = PlatformDirs


if __name__ == "__main__":
    # ---- self test code
    appname = "MyApp"
    appauthor = "MyCompany"

    props = ("user_data_dir",
             "user_config_dir",
             "user_cache_dir",
             "user_state_dir",
             "user_log_dir",
             "site_data_dir",
             "site_config_dir")

    print("-- app dirs %s --" % __version__)

    print("-- app dirs (with optional 'version')")
    dirs = PlatformDirs(appname, appauthor, version="1.0")
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'version')")
    dirs = PlatformDirs(appname, appauthor)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (without optional 'appauthor')")
    dirs = PlatformDirs(appname)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))

    print("\n-- app dirs (with disabled 'appauthor')")
    dirs = PlatformDirs(appname, appauthor=False)
    for prop in props:
        print("%s: %s" % (prop, getattr(dirs, prop)))
