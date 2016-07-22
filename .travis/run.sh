#!/bin/bash
set -e
set -x

# We want to create the virtual environment here, but not actually run anything
tox --notest

# If we have a VENDOR=no then we want to reinstall pip into the virtual
# environment without the vendor directory included as well as install the
# dependencies we need installed.
if [[ $VENDOR = "no" ]]; then
    # Install our dependencies if we're not installing from wheels
    if [[ $WHEELS != "yes" ]]; then
        .tox/$TOXENV/bin/pip install -r pip/_vendor/vendor.txt --no-deps
    fi

    # Install our dependencies if we're installing from wheels
    if [[ $WHEELS = "yes" ]]; then
        mkdir -p /tmp/wheels
        pip wheel --wheel-dir /tmp/wheels --no-deps -r pip/_vendor/vendor.txt
        cp /tmp/wheels/* `echo .tox/$TOXENV/lib/python*/site-packages/pip/_vendor/`
    fi

    # Remove the vendored dependencies from within the installed pip inside of
    # our installed copy of pip.
    find .tox/$TOXENV/lib/python*/site-packages/pip/_vendor -d \
        -not -regex '.*/pip/_vendor/__init__\.py$' \
        -not -regex '.*/pip/_vendor$' \
        -exec rm -rf {} \;

    # Patch our installed pip/_vendor/__init__.py so that it knows to look for
    # the vendored dependencies instead of only looking for the vendored.
    sed -i 's/DEBUNDLED = False/DEBUNDLED = True/' \
        .tox/$TOXENV/lib/python*/site-packages/pip/_vendor/__init__.py

    # Test to make sure that we successfully installed without vendoring
    if [ -f .tox/$TOXENV/lib/python*/site-packages/pip/_vendor/six.py ]; then
        echo "Did not successfully unvendor"
        exit 1
    fi
fi

# Run the unit tests
tox -- -m unit

# Run our integration tests
tox -- -m integration -n 8
