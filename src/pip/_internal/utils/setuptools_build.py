import sys

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import List, Optional, Sequence

# Shim to wrap setup.py invocation with setuptools
#
# We set sys.argv[0] to the path to the underlying setup.py file so
# setuptools / distutils don't take the path to the setup.py to be "-c" when
# invoking via the shim.  This avoids e.g. the following manifest_maker
# warning: "warning: manifest_maker: standard file '-c' not found".
_SETUPTOOLS_SHIM = (
    "import sys, setuptools, tokenize; sys.argv[0] = {0!r}; __file__={0!r};"
    "f=getattr(tokenize, 'open', open)(__file__);"
    "code=f.read().replace('\\r\\n', '\\n');"
    "f.close();"
    "exec(compile(code, __file__, 'exec'))"
)


def make_setuptools_shim_args(
    setup_py_path,  # type: str
    global_options=None,  # type: Sequence[str]
    no_user_config=False,  # type: bool
    unbuffered_output=False  # type: bool
):
    # type: (...) -> List[str]
    """
    Get setuptools command arguments with shim wrapped setup file invocation.

    :param setup_py_path: The path to setup.py to be wrapped.
    :param global_options: Additional global options.
    :param no_user_config: If True, disables personal user configuration.
    :param unbuffered_output: If True, adds the unbuffered switch to the
     argument list.
    """
    args = [sys.executable]
    if unbuffered_output:
        args += ["-u"]
    args += ["-c", _SETUPTOOLS_SHIM.format(setup_py_path)]
    if global_options:
        args += global_options
    if no_user_config:
        args += ["--no-user-cfg"]
    return args


def make_setuptools_develop_args(
    setup_py_path,  # type: str
    global_options,  # type: Sequence[str]
    install_options,  # type: Sequence[str]
    no_user_config,  # type: bool
    prefix,  # type: Optional[str]
):
    # type: (...) -> List[str]
    args = make_setuptools_shim_args(
        setup_py_path,
        global_options=global_options,
        no_user_config=no_user_config,
    )

    args += ["develop", "--no-deps"]

    args += install_options

    if prefix:
        args += ["--prefix", prefix]

    return args


def make_setuptools_egg_info_args(
    setup_py_path,  # type: str
    egg_info_dir,  # type: Optional[str]
    no_user_config,  # type: bool
):
    # type: (...) -> List[str]
    args = make_setuptools_shim_args(setup_py_path)
    if no_user_config:
        args += ["--no-user-cfg"]

    args += ["egg_info"]

    if egg_info_dir:
        args += ["--egg-base", egg_info_dir]

    return args


def make_setuptools_install_args(
    setup_py_path,  # type: str
    global_options,  # type: Sequence[str]
    install_options,  # type: Sequence[str]
    record_filename,  # type: str
    root,  # type: Optional[str]
    prefix,  # type: Optional[str]
    header_dir,  # type: Optional[str]
    no_user_config,  # type: bool
    pycompile  # type: bool
):
    # type: (...) -> List[str]
    args = make_setuptools_shim_args(
        setup_py_path,
        global_options=global_options,
        no_user_config=no_user_config,
        unbuffered_output=True
    )
    args += ["install", "--record", record_filename]
    args += ["--single-version-externally-managed"]

    if root is not None:
        args += ["--root", root]
    if prefix is not None:
        args += ["--prefix", prefix]

    if pycompile:
        args += ["--compile"]
    else:
        args += ["--no-compile"]

    if header_dir:
        args += ["--install-headers", header_dir]

    args += install_options

    return args
