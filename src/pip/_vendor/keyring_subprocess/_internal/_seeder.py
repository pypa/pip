"""Extensions for virtualenv Seeders to pre-install keyring-subprocess."""
import functools
import re
import abc
from functools import update_wrapper
from pathlib import Path

import virtualenv.seed.wheels.embed
import virtualenv.seed.wheels.bundle
from virtualenv.seed.wheels import Version, Wheel
from virtualenv.seed.embed.via_app_data.via_app_data import FromAppData

BUNDLE_SUPPORT = {
    "3.11": {
        "keyring-subprocess": "keyring_subprocess-0.9.0-py3-none-any.whl",
    },
    "3.10": {
        "keyring-subprocess": "keyring_subprocess-0.9.0-py3-none-any.whl",
    },
    "3.9": {
        "keyring-subprocess": "keyring_subprocess-0.9.0-py3-none-any.whl",
    },
    "3.8": {
        "keyring-subprocess": "keyring_subprocess-0.9.0-py3-none-any.whl",
    },
    "3.7": {
        "keyring-subprocess": "keyring_subprocess-0.9.0-py3-none-any.whl",
    },
}
MAX = "3.11"


def pep503(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize(name):
    return pep503(name).replace("-", "_")


def _get_embed_wheel(wrapped, distribution: str, for_py_version: str, *args, **kwargs):
    if normalize(distribution) == normalize("keyring-subprocess"):
        wheel = (
            virtualenv.seed.wheels.embed.BUNDLE_SUPPORT.get(for_py_version, {})
            or virtualenv.seed.wheels.embed.BUNDLE_SUPPORT[MAX]
        ).get("keyring-subprocess")

        wheel = None if wheel is None else Path(__file__).parent / "wheels" / wheel
        wheel = None if wheel is None or not wheel.exists() else wheel

        return Wheel.from_path(wheel)
    else:
        return wrapped(distribution, for_py_version, *args, **kwargs)


_get_embed_wheel = functools.partial(
    _get_embed_wheel, virtualenv.seed.wheels.embed.get_embed_wheel
)
update_wrapper(_get_embed_wheel, virtualenv.seed.wheels.embed.get_embed_wheel)
virtualenv.seed.wheels.bundle.get_embed_wheel = _get_embed_wheel

for (
    for_py_version,
    distribution_to_package,
) in virtualenv.seed.wheels.embed.BUNDLE_SUPPORT.items():
    version = tuple(map(int, for_py_version.split(".")))
    if version >= (3, 7):
        distribution_to_package["keyring-subprocess"] = (
            BUNDLE_SUPPORT.get(for_py_version, {}) or BUNDLE_SUPPORT[MAX]
        ).get("keyring-subprocess")


class ParserWrapper:
    def __init__(self, parser):
        self.parser = parser

    def __getattr__(self, item):
        return getattr(self.parser, item)

    def add_argument(self, *args, **kwargs):
        if "dest" in kwargs and (
            ("metavar" in kwargs and kwargs["metavar"] == "version")
            or any(
                arg for arg in args if isinstance(arg, str) and arg.startswith("--no-")
            )
        ):
            kwargs["dest"] = normalize(kwargs["dest"])

        self.parser.add_argument(*args, **kwargs)


class Normalize:
    def __enter__(self):
        KeyringSubprocessFromAppData.normalize = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        KeyringSubprocessFromAppData.normalize = False


class MetaClass(abc.ABCMeta):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        if not hasattr(cls, "normalize"):
            cls.normalize = False


class KeyringSubprocessFromAppData(FromAppData, metaclass=MetaClass):
    """Mixed in keyring-subprocess into seed packages for app-data seeder."""

    def __init__(self, options):
        """Add the extra attributes for the extensions."""
        self.keyring_subprocess_version = options.keyring_subprocess
        self.no_keyring_subprocess = options.no_keyring_subprocess

        super(KeyringSubprocessFromAppData, self).__init__(options)

    @classmethod
    def add_parser_arguments(cls, parser, interpreter, app_data):
        parser = ParserWrapper(parser)

        super(KeyringSubprocessFromAppData, cls).add_parser_arguments(
            parser, interpreter, app_data
        )

    @classmethod
    def distributions(cls):
        """Return the dictionary of distributions."""
        distributions = super(KeyringSubprocessFromAppData, cls).distributions()
        distributions["keyring-subprocess"] = Version.bundle

        if cls.normalize:
            distributions = {
                normalize(distribution): version
                for distribution, version in distributions.items()
            }

        return distributions

    def distribution_to_versions(self):
        with Normalize():
            return super().distribution_to_versions()

    def __str__(self):
        with Normalize():
            return super().__str__()

    def __repr__(self):
        with Normalize():
            return super().__repr__()
