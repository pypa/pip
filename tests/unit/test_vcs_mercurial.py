"""
Contains functional tests of the Mercurial class.
"""

import configparser
import os

from pip._internal.utils.misc import hide_url
from pip._internal.vcs.mercurial import Mercurial
from tests.lib import need_mercurial


@need_mercurial
def test_mercurial_switch_updates_config_file_when_found(tmpdir):
    hg = Mercurial()
    options = hg.make_rev_options()
    hg_dir = os.path.join(tmpdir, ".hg")
    os.mkdir(hg_dir)

    config = configparser.RawConfigParser()
    config.add_section("paths")
    config.set("paths", "default", "old_url")

    hgrc_path = os.path.join(hg_dir, "hgrc")
    with open(hgrc_path, "w") as f:
        config.write(f)
    hg.switch(tmpdir, hide_url("new_url"), options)

    config.read(hgrc_path)

    default_path = config.get("paths", "default")
    assert default_path == "new_url"
