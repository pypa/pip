#!/bin/bash
set -e
set -x

if [[ $TOXENV == py* ]]; then
    # Run unit tests
    tox -- -m unit
    # Run integration tests
    tox -- -m integration -n 4 --duration=5
else
    # Run once
    tox
fi
