#!/usr/bin/env python
import os
import tox

if not os.environ.get("TOXENV"):
    if os.environ["TRAVIS_PYTHON_VERSION"] == "pypy":
        os.environ["TOXENV"] = "pypy"
    else:
        os.environ["TOXENV"] = "py{0}".format(
            "".join(os.environ["TRAVIS_PYTHON_VERSION"].split(".")[:2]),
        )

tox.cmdline()
