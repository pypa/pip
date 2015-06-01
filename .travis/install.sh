#!/bin/bash
set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

pip install --upgrade setuptools
pip install coverage diff_cover tox

# If we're running under Python 3.5, then we need to actually go and install
# Python 3.5.
if [[ $TOXENV = "py35" ]]; then
    sudo python-build 3.5-dev /opt/python/3.5-dev
fi
