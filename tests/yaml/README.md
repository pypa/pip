# Fixtures

This directory contains fixtures for testing pip's resolver.
The fixtures are written as `.yml` files, with a convenient format
that allows for specifying a custom index for temporary use.

The `.yml` files are organized in the following way.  A `base` section
which ...

The linter is very useful for initally checking `.yml` files, e.g.:

    $ python linter.py -v simple.yml

To run only the yaml tests, use (from the root of the source tree):

    $ tox -e py38 -- -m yaml -vv


<!-- TODO: Add a good description of the format and how it can be used. -->
