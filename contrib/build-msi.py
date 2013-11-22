#!/usr/bin/env python
"""
Builds an MSI installer for pip + setuptools
"""
import msilib
import os
import os.path
import shutil
import subprocess
import sys
import tarfile
import platform

from distutils.command.bdist_msi import bdist_msi

SETUPTOOLS = "1.1.6"

PYTHON_VERSION = ".".join(map(str, sys.version_info[:2]))
PYTHON_VERSION_NODOT = "".join(map(str, sys.version_info[:2]))
PYTHON_NAME = "Python{}".format(PYTHON_VERSION_NODOT)
PYTHON_ARCH_NODOT = "amd64" if platform.architecture()[0] == "64bit" else ""
PYTHON_ARCH = "." + PYTHON_ARCH_NODOT

BUILD_DIR = os.path.abspath("build/msi-staging")
PYTHON_DIR = os.path.join(BUILD_DIR, os.path.splitdrive(sys.prefix)[1][1:])
LIB_DIR = os.path.join(PYTHON_DIR, "Lib")
BIN_DIR = os.path.join(PYTHON_DIR, "Scripts")
SITE_PACKAGES = os.path.join(LIB_DIR, "site-packages")

if sys.version_info[:1] == (3,):
    get_unbound_function = lambda x: x
else:
    def get_unbound_function(unbound):
        return unbound.im_func


class _FakeDistribution(object):

    def __init__(self, name, version):
        self.name = name
        self.version = version

    def get_fullname(self):
        return "{}-{}".format(self.name, self.version)


class _FakeCommand(object):

    other_version = bdist_msi.other_version
    target_version = PYTHON_VERSION
    versions = [target_version]

    install_script = None

    def __init__(self, bdist_dir, db, dist):
        self.bdist_dir = bdist_dir
        self.db = db
        self.distribution = _FakeDistribution(*dist)


def create_msi(path, version, author, email, url):
    product_name = "pip - Python {}{}".format(
        PYTHON_VERSION,
        " ({})".format(PYTHON_ARCH_NODOT) if PYTHON_ARCH_NODOT else "",
    )
    installer_name = "dist/pip-{}-py{}{}.msi".format(
        version,
        PYTHON_VERSION_NODOT,
        PYTHON_ARCH if PYTHON_ARCH != "." else "",
    )

    print("Creating {}".format(installer_name))

    db = msilib.init_database(
        installer_name,
        msilib.schema,
        product_name,
        msilib.gen_uuid(),
        version,
        author,
    )
    msilib.add_tables(db, msilib.sequence)
    msilib.add_data(
        db,
        "Property",
        [
            ("DistVersion", version),
            ("ARPCONTACT", email),
            ("ARPURLINFOABOUT", url),
        ],
    )

    # Use the code in distutils to add the "Find Python" dialog
    get_unbound_function(bdist_msi.add_find_python)(
        _FakeCommand(PYTHON_DIR, db, (product_name, version)),
    )

    # Use the code in distutils to add files to the msi
    get_unbound_function(bdist_msi.add_files)(
        _FakeCommand(PYTHON_DIR, db, (product_name, version))
    )

    # Use the code in distutils to add a ui to the msi
    get_unbound_function(bdist_msi.add_ui)(
        _FakeCommand(PYTHON_DIR, db, (product_name, version))
    )

    # Commit all our changes
    db.Commit()


def install(project, path, command):
    subprocess.check_call(
        [
            "python", "setup.py", "install", "--root", BUILD_DIR,
            "--no-compile", "-O0",
        ],
        cwd=path,
    )


if __name__ == "__main__":
    # Ensure our build directory is empty
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    # Create a new and empty build directory
    os.makedirs(BUILD_DIR)

    # Extract setuptools to a temporary location
    with tarfile.open("contrib/setuptools-%s.tar.gz" % SETUPTOOLS) as tar:
        tar.extractall(BUILD_DIR)

    setuptools_dir = os.path.join(BUILD_DIR, "setuptools-%s" % SETUPTOOLS)

    # Install setuptools
    install("setuptools", setuptools_dir, "easy_install")

    # Install pip
    install("pip", ".", "pip")

    # Get the version by executing the setup.py script
    version = subprocess.check_output(
        ["python", "setup.py", "--version"]
    ).strip().decode("utf8")

    # Create the msi using the staged files
    create_msi(
        PYTHON_DIR,
        version,
        "Python Packaging Authority",
        "pypa-dev@groups.google.com",
        "http://www.pip-installer.org/",
    )

    # A simple note to remember the commands
    print('Sign using: signtool sign /t http://timestamp.digicert.com /f '
          '"c:\path\to\mycert.pfx" /p pfxpassword /d "pip - Python 2.7 (64bit)'
          '" "c:\path\to\file.exe"')
