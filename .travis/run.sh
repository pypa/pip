#!/bin/bash
set -e
set -x

# If we're running under Python 3.5, we can't use anything but --asert=plain
if [[ $TOXENV = "py35" ]]; then
    export TOXARGS="--assert=plain"
fi

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

    # Actually install pip without the bundled dependencies
    PIP_NO_VENDOR_FOR_DOWNSTREAM=1 .tox/$TOXENV/bin/pip install .

    # Install our dependencies if we're installing from wheels
    if [[ $WHEELS = "yes" ]]; then
        mkdir -p /tmp/wheels
        pip wheel --wheel-dir /tmp/wheels --no-deps -r pip/_vendor/vendor.txt
        cp /tmp/wheels/* `echo .tox/$TOXENV/lib/python*/site-packages/pip/_vendor/`
    fi

    # Test to make sure that we successfully installed without vendoring
    if [ -f .tox/$TOXENV/lib/python*/site-packages/pip/_vendor/six.py ]; then
        echo "Did not successfully unvendor"
        exit 1
    fi
fi

# Run the unit tests
tox -- -m unit --cov pip/ --cov-report xml $TOXARGS

# Run our integration tests
# Note: There is an issue with Python 3.2 where concurrent imports will corrupt
#       the generated .pyc files and we'll get very strange errors. However as
#       long as we continue to run the unit tests first and in a seperate step
#       then this should work fine.
tox -- -m integration -n 8 $TOXARGS
