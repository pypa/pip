#!/bin/bash
set -e
set -x

# This is required in order to get UTF-8 output inside of the subprocesses that
# our tests use.
export LC_CTYPE=en_US.UTF-8

# Run the unit tests
tox -- -m unit

# Run our integration tests, typically with pytest-xdist to speed things up
# except on Python 3.2 where it doesn't work quite right.
case $TOXENV in
    py32)
        tox -- -m integration
        ;;
    *)
        tox -- -m integration -n 8
        ;;
esac
