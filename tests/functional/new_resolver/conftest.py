import json
import os

import pytest
from pip._vendor.packaging.utils import canonicalize_name


@pytest.fixture()
def script(script):
    def pip_install_new_resolver(*args, **kwargs):
        return script.pip(
            "install",
            "--use-feature=2020-resolver",
            "--no-cache-dir",
            "--no-index",
            *args,
            **kwargs  # Python 2.7 fails on trailing comma.
        )

    def assert_installed(**kwargs):
        ret = script.pip("list", "--format=json")
        installed = set(
            (canonicalize_name(val["name"]), val["version"])
            for val in json.loads(ret.stdout)
        )
        expected = set((canonicalize_name(k), v) for k, v in kwargs.items())
        assert expected <= installed, \
            "{!r} not all in {!r}".format(expected, installed)

    def assert_not_installed(*args):
        ret = script.pip("list", "--format=json")
        installed = set(
            canonicalize_name(val["name"])
            for val in json.loads(ret.stdout)
        )
        # None of the given names should be listed as installed, i.e. their
        # intersection should be empty.
        expected = set(canonicalize_name(k) for k in args)
        assert not (expected & installed), \
            "{!r} contained in {!r}".format(expected, installed)

    def assert_editable(*args):
        # This simply checks whether all of the listed packages have a
        # corresponding .egg-link file installed.
        # TODO: Implement a rigorous way to test for editable installations.
        site_packages_path = script.site_packages_path
        egg_links = set("{}.egg-link".format(arg) for arg in args)
        assert egg_links <= set(os.listdir(site_packages_path)), \
            "{!r} not all found in {!r}".format(args, site_packages_path)

    script.pip_install_new_resolver = pip_install_new_resolver
    script.assert_installed = assert_installed
    script.assert_not_installed = assert_not_installed
    script.assert_editable = assert_editable
    return script
