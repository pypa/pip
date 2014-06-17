#!/bin/bash
set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

sudo apt-get install mtr-tiny

mtr -w -r -c 5 23.235.46.175

sudo ifconfig

pip install .
pip install --upgrade setuptools
pip install tox
