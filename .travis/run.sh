#!/bin/bash
set -e
set -x

# Short circuit tests and linting jobs if there are no code changes involved.
if [[ $TOXENV != docs ]]; then
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
            echo "Only Documentation was updated -- skipping build."
            exit
        fi
    fi
fi

if [[ $TOXENV == *-functional-install ]]; then
    # Only run slow/network integration tests
    tox -- -m integration -n 4 --duration=5 --only_install_tests
elif [[ $TOXENV == py* ]]; then
    # Run unit tests
    tox -- -m unit
    # Run integration tests
    tox -- -m integration -n 4 --duration=5
else
    # Run once
    tox
fi
