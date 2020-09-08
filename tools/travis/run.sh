#!/bin/bash
set -e

# Short circuit test runs if there are no code changes involved.
if [[ $TOXENV != docs ]] || [[ $TOXENV != lint ]]; then
    if [[ "$TRAVIS_PULL_REQUEST" == "false" ]]
    then
        echo "This is not a PR -- will do a complete build."
    else
        # Pull requests are slightly complicated because $TRAVIS_COMMIT_RANGE
        # may include more changes than desired if the history is convoluted.
        # Instead, explicitly fetch the base branch and compare against the
        # merge-base commit.
        git fetch -q origin +refs/heads/$TRAVIS_BRANCH
        changes=$(git diff --name-only HEAD $(git merge-base HEAD FETCH_HEAD))
        echo "Files changed:"
        echo "$changes"
        if ! echo "$changes" | grep -qvE '(\.rst$)|(^docs)|(^news)|(^\.github)'
        then
            echo "Code was not changed -- skipping build."
            exit
        fi
    fi
fi

# Export the correct TOXENV when not provided.
echo "Determining correct TOXENV..."
if [[ -z "$TOXENV" ]]; then
    if [[ ${TRAVIS_PYTHON_VERSION} == pypy* ]]; then
        export TOXENV=pypy
    else
        # We use the syntax ${string:index:length} to make 2.7 -> py27
        _major=${TRAVIS_PYTHON_VERSION:0:1}
        _minor=${TRAVIS_PYTHON_VERSION:2:1}
        export TOXENV="py${_major}${_minor}"
    fi
fi
echo "TOXENV=${TOXENV}"

if [[ -z "$NEW_RESOLVER" ]]; then
    RESOLVER_SWITCH=''
else
    RESOLVER_SWITCH='--new-resolver'
fi

# Print the commands run for this test.
set -x
if [[ "$GROUP" == "1" ]]; then
    # Unit tests
    tox -- --use-venv -m unit -n auto
    # Integration tests (not the ones for 'pip install')
    tox -- -m integration -n auto --durations=5 -k "not test_install" \
        --use-venv $RESOLVER_SWITCH
elif [[ "$GROUP" == "2" ]]; then
    # Separate Job for running integration tests for 'pip install'
    tox -- -m integration -n auto --durations=5 -k "test_install" \
        --use-venv $RESOLVER_SWITCH
elif [[ "$GROUP" == "3" ]]; then
    # Separate Job for tests that fail with the new resolver
    tox -- -m fails_on_new_resolver -n auto --durations=5 \
        --use-venv $RESOLVER_SWITCH --new-resolver-runtests
else
    # Non-Testing Jobs should run once
    tox
fi
