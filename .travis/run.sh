#!/bin/bash
set -e
set -x

# This is required in order to get UTF-8 output inside of the subprocesses that
# our tests use.
export LC_CTYPE=en_US.UTF-8

# We'll set the tox env based on the Travis Python version but only if we do
# not have an explicit TOXENV
if [ -z "$TOXENV" ]; then
    # First we'll set the start of our tox environment string based on the
    # Travis Python version
    if [[ $TRAVIS_PYTHON_VERSION =~ [23]\.[0-9] ]]; then
        export TOXENV=py`echo $TRAVIS_PYTHON_VERSION | sed 's/\.//'`;
    else
        export TOXENV=$TRAVIS_PYTHON_VERSION;
    fi

    # Then we need to add our test suite type
    export TOXENV="${TOXENV}-${SUITE}"
fi

# Actually run our tests
tox
