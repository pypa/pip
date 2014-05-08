#!/bin/bash
set -e
set -x

# This is required in order to get UTF-8 output inside of the subprocesses that
# our tests use.
export LC_CTYPE=en_US.UTF-8

case $TOXENV in
    py32)
        tox
        ;;
    *)
        tox -- -n 8
        ;;
esac
