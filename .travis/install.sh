#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == "Darwin" ]]; then
    brew update
    brew install pyenv
    if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi
    case "${TOX_ENV}" in
        py26)
            pyenv install 2.6.9
            pyenv global 2.6.9
            ;;
        py27)
            pyenv install 2.7.6
            pyenv global 2.7.6
            ;;
        pypy)
            pyenv install pypy-2.2.1
            pyenv global pypy-2.2.1
            ;;
        py32)
            pyenv install 3.2.5
            pyenv global 3.2.5
            ;;
        py33)
            pyenv install 3.3.5
            pyenv global 3.3.5
            ;;
        py34)
            pyenv install 3.4.0
            pyenv global 3.4.0
            ;;
    esac

    # Install subversion
    if [[ "$(brew list | grep subversion)" != "subversion" ]]; then
      brew install subversion
    fi

    # Install bazaar
    if [[ "$(brew list | grep bazaar)" != "bazaar" ]]; then
      brew install bazaar
    fi

    # Install mercurial
    if [[ "$(brew list | grep mercurial)" != "mercurial" ]]; then
      brew install mercurial
    fi

    # Rehash our pyenv
    pyenv rehash

    # Install setuptools
    pip install --upgrade setuptools

    # Install tox
    pip install --upgrade tox

    # Rehash our pyenv
    pyenv rehash
else
    # add mega-python ppa
    sudo add-apt-repository -y ppa:fkrull/deadsnakes
    sudo apt-get -y update

    case "${TOXENV}" in
        py26)
            sudo apt-get install python2.6 python2.6-dev
            ;;
        py32)
            sudo apt-get install python3.2 python3.2-dev
            ;;
        py33)
            sudo apt-get install python3.3 python3.3-dev
            ;;
        py34)
            sudo apt-get install python3.4 python3.4-dev
            ;;
        py3pep8)
            sudo apt-get install python3 python3-dev
            ;;
        pypy)
            sudo add-apt-repository -y ppa:pypy/ppa
            sudo apt-get -y update
            sudo apt-get install -y --force-yes pypy pypy-dev
            ;;
    esac

    # Install setuptools
    sudo pip install --upgrade setuptools

    # Install tox
    sudo pip install --upgrade tox

    # Install all the required VCSs
    sudo apt-get install subversion bzr mercurial

    # Check the SSL Certificates for HG
    echo -e "[web]\ncacerts = /etc/ssl/certs/ca-certificates.crt" >> ~/.hgrc
fi
