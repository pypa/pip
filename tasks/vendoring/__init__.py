""""Vendoring script, python 3.5 needed"""

from pathlib import Path
import re
import shutil

import invoke

TASK_NAME = 'update'

FILE_WHITE_LIST = (
    'Makefile',
    'vendor.txt',
    '__init__.py',
    'README.rst',
)


def drop_dir(path):
    shutil.rmtree(str(path))


def remove_all(paths):
    for path in paths:
        if path.is_dir():
            drop_dir(path)
        else:
            path.unlink()


def log(msg):
    print('[vendoring.%s] %s' % (TASK_NAME, msg))


def clean_vendor(ctx, vendor_dir):
    # Old _vendor cleanup
    remove_all(vendor_dir.glob('*.pyc'))
    log('Cleaning %s' % vendor_dir)
    for item in vendor_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(str(item))
        elif item.name not in FILE_WHITE_LIST:
            item.unlink()
        else:
            log('Skipping %s' % item)


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


def apply_patch(ctx, patch_file_path):
    log('Applying patch %s' % patch_file_path.name)
    ctx.run('git apply %s' % patch_file_path)


def vendor(ctx, vendor_dir):
    log('Reinstalling vendored libraries')
    ctx.run(
        'pip install -t {0} -r {0}/vendor.txt --no-compile'.format(
            str(vendor_dir),
        )
    )
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
    log("Detected vendored libraries: %s" % ", ".join(vendored_libs))

    # Global import rewrites
    log("Rewriting all imports related to vendored libs")
    for item in vendor_dir.iterdir():
        if item.is_dir():
            rewrite_imports(item, vendored_libs)
        elif item.name not in FILE_WHITE_LIST:
            rewrite_file_imports(item, vendored_libs)

    # Special cases: apply stored patches
    log("Apply patches")
    patch_dir = Path(__file__).parent / 'patches'
    for patch in patch_dir.glob('*.patch'):
        apply_patch(ctx, patch)


@invoke.task(name=TASK_NAME)
def main(ctx):
    git_root = Path(
        ctx.run('git rev-parse --show-toplevel', hide=True).stdout.strip()
    )
    vendor_dir = git_root / 'pip' / '_vendor'
    log('Using vendor dir: %s' % vendor_dir)
    clean_vendor(ctx, vendor_dir)
    vendor(ctx, vendor_dir)
    log('Revendoring complete')
