from email.parser import FeedParser
import os
import imp
import locale
import re
import sys
import shutil
import tempfile
import textwrap
import zipfile

from distutils.util import change_root
from pip.locations import (bin_py, running_under_virtualenv,PIP_DELETE_MARKER_FILENAME,
                           write_delete_marker_file, bin_user)
from pip.exceptions import (InstallationError, UninstallationError, UnsupportedWheel,
                            BestVersionAlreadyInstalled, InvalidWheelFilename,
                            DistributionNotFound, PreviousBuildDirError)
from pip.vcs import vcs
from pip.log import logger
from pip.util import (display_path, rmtree, ask, ask_path_exists, backup_dir,
                      is_installable_dir, is_local, dist_is_local,
                      dist_in_usersite, dist_in_site_packages, renames,
                      normalize_path, egg_link_path, make_path_relative,
                      call_subprocess, is_prerelease, normalize_name)
from pip.backwardcompat import (urlparse, urllib, uses_pycache,
                                ConfigParser, string_types, HTTPError,
                                get_python_version, b)
from pip.index import Link
from pip.locations import build_prefix
from pip.download import (PipSession, get_file_content, is_url, url_to_path,
                          path_to_url, is_archive_file,
                          unpack_vcs_link, is_vcs_url, is_file_url,
                          unpack_file_url, unpack_http_url)
import pip.wheel
from pip.wheel import move_wheel_files, Wheel, wheel_ext
from pip._vendor import pkg_resources


