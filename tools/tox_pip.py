"""A simple wrapper to ensure tox always uses a known-good pip.
"""

import distutils.sysconfig
import itertools
import os
import shutil
import subprocess
import sys
from glob import glob
from os.path import basename, exists, join

VIRTUAL_ENV = os.environ["VIRTUAL_ENV"]
SITE_PACKAGES = distutils.sysconfig.get_python_lib()

TOX_PIP_DIR = join(VIRTUAL_ENV, "pip-backup")
EXECUTABLE_BACKUP = join(TOX_PIP_DIR, "bin")
PACKAGE_BACKUP = join(TOX_PIP_DIR, "package")


# Logic for finding the right files
def get_installed_files(where):
    sources = join(where, "pip")
    dist_infos = glob(join(where, "pip-*.dist-info"))
    egg_stuff = glob(join(where, "pip*.egg-*"))

    return filter(exists, itertools.chain([sources], dist_infos, egg_stuff))


def get_binaries(where):
    return glob(join(where, "bin", "pip*"))


# Logic for moving the files around.
def backup_as_known_good():
    # Make the backup directory
    os.mkdir(TOX_PIP_DIR)

    # Copy executable/launchers.
    os.mkdir(EXECUTABLE_BACKUP)
    for entry in get_binaries(VIRTUAL_ENV):
        shutil.copy2(entry, join(EXECUTABLE_BACKUP, basename(entry)))

    # Copy package and distribution info.
    os.mkdir(PACKAGE_BACKUP)
    for path in get_installed_files(SITE_PACKAGES):
        shutil.copytree(path, join(PACKAGE_BACKUP, basename(path)))


def remove_existing_installation():
    # Remove executables/launchers.
    for entry in get_binaries(VIRTUAL_ENV):
        os.unlink(entry)

    # Remove package and distribution info.
    for path in get_installed_files(SITE_PACKAGES):
        if os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)


def install_known_good_pip():
    # Copy executables/launchers.
    for entry in get_binaries(TOX_PIP_DIR):
        shutil.copy2(entry, join(VIRTUAL_ENV, "bin", basename(entry)))

    # Move package and distribution info.
    for path in get_installed_files(PACKAGE_BACKUP):
        shutil.copytree(path, join(SITE_PACKAGES, basename(path)))


def run(args):
    # First things first, safeguard the environment original pip so it can be
    # used for all calls.
    if not exists(TOX_PIP_DIR):
        backup_as_known_good()

    remove_existing_installation()
    install_known_good_pip()

    # Run the command.
    #   We just do a python -m pip here because this is a known good pip, which
    #   is expected to work properly.
    cmd = [sys.executable, "-m", "pip"]
    cmd.extend(args)
    subprocess.check_call(cmd)


if __name__ == "__main__":
    run(sys.argv[1:])
