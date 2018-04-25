#!/bin/bash
set -e
set -x

export PATH="$PATH:$HOME/.p4/bin"

if [[ $TOXENV == py* ]]; then
    # Run unit tests
    tox -- -m unit
    # Run integration tests
    tox -- -m integration -n 4 --duration=5
else
    # Run once
    tox
fi
