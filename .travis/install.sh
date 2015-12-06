#!/bin/bash
set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

pip install --upgrade setuptools
pip install --upgrade tox

pip list

# Make sure wheel is not installed for system_site_packages virtualenvs
pip uninstall --yes wheel || true
