#!/bin/bash
set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

pip install --upgrade setuptools
pip install --upgrade tox

wget -N -P "$HOME/.p4/bin" \
    "http://ftp.perforce.com/perforce/r17.2/bin.linux26x86_64/p4" \
    "http://ftp.perforce.com/perforce/r17.2/bin.linux26x86_64/p4d"
chmod +x \
    "$HOME/.p4/bin/p4" \
    "$HOME/.p4/bin/p4d"
