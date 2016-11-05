""""Vendoring script, python 3.5 needed"""

from pathlib import Path
import re
import shutil
import subprocess

import pip


FILE_WHITE_LIST = (
    'Makefile',
    'vendor.txt',
    '__init__.py',
    'README.rst',
)


SPECIAL_CASES = (
    # Modified distro to delay importing argparse to avoid errors on 2.6
    (
        'distro.py',
        """\
import logging
import argparse
import subprocess""",
        """\
import logging
import subprocess""",
    ),
    (
        'distro.py',
        r'def main():',
        r'def main():\n    import argparse\n',
    ),
    # Remove unvendored requests special case
    (
        'cachecontrol/compat.py',
        """\
# Handle the case where the requests module has been patched to not have
# urllib3 bundled as part of its source.
try:
    from pip._vendor.requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse

try:
    from pip._vendor.requests.packages.urllib3.util import is_fp_closed
except ImportError:
    from urllib3.util import is_fp_closed""",
        """\
from pip._vendor.requests.packages.urllib3.response import HTTPResponse
from pip._vendor.requests.packages.urllib3.util import is_fp_closed""",
    ),
    # requests has been modified *not* to optionally load any C dependencies
    (
        'requests/__init__.py',
        """\
try:
    from .packages.urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()
except ImportError:
    pass""",
        """\
# Note: Patched by pip to prevent using the PyOpenSSL module. On Windows this
#       prevents upgrading cryptography.
# try:
#     from .packages.urllib3.contrib import pyopenssl
#     pyopenssl.inject_into_urllib3()
# except ImportError:
#     pass""",
    ),
    (
        'requests/compat.py',
        """\
try:
    import simplejson as json
except (ImportError, SyntaxError):
    # simplejson does not support Python 3.2, it throws a SyntaxError
    # because of u'...' Unicode literals.
    import json""",
        """\
# Note: We've patched out simplejson support in pip because it prevents
#       upgrading simplejson on Windows.
# try:
#     import simplejson as json
# except (ImportError, SyntaxError):
#     # simplejson does not support Python 3.2, it throws a SyntaxError
#     # because of u'...' Unicode literals.
import json""",
    )
)


def drop_dir(path):
    shutil.rmtree(str(path))


def remove_all(paths):
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()


def clean_vendor(vendor_dir):
    # Old _vendor cleanup
    remove_all(vendor_dir.glob('*.pyc'))
    for item in vendor_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(str(item))
        elif item.name not in FILE_WHITE_LIST:
            item.unlink()


def rewrite_imports(package_dir, vendored_libs):
    for item in package_dir.iterdir():
        if item.is_dir():
            rewrite_imports(item, vendored_libs)
        elif item.name.endswith('.py'):
            rewrite_file_imports(item, vendored_libs)


def rewrite_file_imports(item, vendored_libs):
    """Rewrite 'import xxx' and 'from xxx import' for vendored_libs"""
    text = item.read_text()
    # Revendor pkg_resources.extern first
    text = re.sub(r'pkg_resources.extern', r'pip._vendor', text)
    for lib in vendored_libs:
        text = re.sub(
            r'(\n\s*)import %s' % lib,
            r'\1from pip._vendor import %s' % lib,
            text,
        )
        text = re.sub(
            r'(\n\s*)from %s' % lib,
            r'\1from pip._vendor.%s' % lib,
            text,
        )
    item.write_text(text)


def apply_special_cases(vendor_dir, special_cases):
    for filename, to_replace, replacement in special_cases:
        patched_file = vendor_dir / filename
        text = patched_file.read_text()
        text, nb_apply = re.subn(
            # Escape parenthesis for re.subn
            to_replace.replace('(', '\\(').replace(')', '\\)'),
            replacement,
            text,
        )
        # Make sure the patch is correctly applied
        assert nb_apply, filename
        patched_file.write_text(text)


def vendor(vendor_dir):
    pip.main([
        'install',
        '-t', str(vendor_dir),
        '-r', str(vendor_dir / 'vendor.txt'),
        '--no-compile',
    ])
    remove_all(vendor_dir.glob('*.dist-info'))
    remove_all(vendor_dir.glob('*.egg-info'))

    # Cleanup setuptools unneeded parts
    (vendor_dir / 'easy_install.py').unlink()
    drop_dir(vendor_dir / 'setuptools')
    drop_dir(vendor_dir / 'pkg_resources' / '_vendor')
    drop_dir(vendor_dir / 'pkg_resources' / 'extern')

    # Detect the vendored packages/modules
    vendored_libs = []
    for item in vendor_dir.iterdir():
        if item.is_dir():
            vendored_libs.append(item.name)
        elif item.name not in FILE_WHITE_LIST:
            vendored_libs.append(item.name[:-3])
    print("Vendored lib: %s" % ", ".join(vendored_libs))

    # Global import rewrites
    for item in vendor_dir.iterdir():
        if item.is_dir():
            rewrite_imports(item, vendored_libs)
        elif item.name not in FILE_WHITE_LIST:
            rewrite_file_imports(item, vendored_libs)

    # Special cases
    apply_special_cases(vendor_dir, SPECIAL_CASES)


def main():
    git_root = Path(subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel']
    ).decode().strip())
    vendor_dir = git_root / 'pip' / '_vendor'
    clean_vendor(vendor_dir)
    vendor(vendor_dir)


if __name__ == '__main__':
    main()
