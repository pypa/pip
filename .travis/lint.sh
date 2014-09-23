#!/bin/bash
set -e
set -x

flake8 .
find -name '*.py' |
    egrep -v '/(_vendor|.tox)/'  |
    grep -vxFf .travis/pylint-grandfathered.txt |
    grep -vxFf .travis/pylint-blacklist.txt |
    xargs pylint -f parseable

echo checking that the grandfather list is correct, too...
cat .travis/pylint-grandfathered.txt |
    grep -v '^\s*#' |
    xargs --replace -P8 sh -c '
        set -e
        if pylint {} > /dev/null; then
            echo {} has no pylint errors!
            echo but it is still in the grandfather list.
            exit 1
        fi
    '
