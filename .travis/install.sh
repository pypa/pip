#!/bin/bash

set -e
set -x

git config --global user.email "python-virtualenv@googlegroups.com"
git config --global user.name "Pip"

pip install --upgrade setuptools
pip install tox
