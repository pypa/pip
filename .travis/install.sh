#!/bin/bash
set -e
set -x

git config --global user.email "pypa-dev@googlegroups.com"
git config --global user.name "pip"

# Use travis_retry to prevent intermittent failures from external factors like
# networking problems or PyPI issues
travis_retry pip install --upgrade setuptools
travis_retry pip install coverage diff_cover tox
