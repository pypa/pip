from glob import glob
import distutils.sysconfig
import os
import shutil
import subprocess
import sys


VIRTUAL_ENV = os.environ['VIRTUAL_ENV']
TOX_PIP_DIR = os.path.join(VIRTUAL_ENV, 'pip')
SITE_PACKAGES = distutils.sysconfig.get_python_lib()


def pip(args):
    # First things first, safeguard the environment
    # original pip so it can be used for all calls.
    if not os.path.exists(TOX_PIP_DIR):
        os.mkdir(TOX_PIP_DIR)
        # Remove executable/launchers.
        for entry in glob(os.path.join(VIRTUAL_ENV, 'bin', 'pip*')):
            os.unlink(entry)
        # Relocate package and distribution info.
        for src in (
            os.path.join(SITE_PACKAGES, 'pip'),
            glob(os.path.join(SITE_PACKAGES, 'pip-*.dist-info'))[0],
        ):
            shutil.move(src, TOX_PIP_DIR)
        # Create a very simple launcher that
        # can be used for Linux and Windows.
        with open(os.path.join(TOX_PIP_DIR, 'pip.py'), 'w') as fp:
            fp.write('from pip import main; main()\n')
    # And use a temporary copy of that version
    # so it can uninstall itself if needed.
    temp_pip = TOX_PIP_DIR + '.tmp'
    try:
        shutil.copytree(TOX_PIP_DIR, temp_pip)
        cmd = [sys.executable, os.path.join(temp_pip, 'pip.py')]
        cmd.extend(args)
        subprocess.check_call(cmd)
    finally:
        shutil.rmtree(temp_pip)


if __name__ == '__main__':
    pip(sys.argv[1:])
