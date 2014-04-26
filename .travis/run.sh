#!/bin/bash

set -e
set -x

source ~/.venv/bin/activate

case $TOXENV in
    py32)
        tox
        ;;
    *)
        tox -- -n 8
        ;;
esac
