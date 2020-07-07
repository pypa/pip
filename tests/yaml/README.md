# YAML tests for pip's resolver

This directory contains fixtures for testing pip's resolver.
The fixtures are written as `.yml` files, with a convenient format
that allows for specifying a custom index for temporary use.

The `.yml` files are typically organized in the following way.  Here, we are
going to take a closer look at the `simple.yml` file and step through the
test cases.  A `base` section defines which packages are available upstream:

    base:
      available:
        - simple 0.1.0
        - simple 0.2.0
        - base 0.1.0; depends dep
        - dep 0.1.0

Each package has a name and version number.  Here, there are two
packages `simple` (with versoin `0.1.0` and `0.2.0`).  The package
`base 0.1.0` depends on the requirement `dep` (which simply means it
depends on any version of `dep`.  More generally, a package can also
depend on a specific version of another package, or a range of versions.

Next, in our yaml file, we have the `cases:` section which is a list of
test cases.  Each test case has a request and a response.  The request
is what the user would want to do:

    cases:
    -
      request:
        - install: simple
        - uninstall: simple
      response:
        - state:
          - simple 0.2.0
        - state: null

Here the first request is to install the package simple, this would
basically be equivalent to typing `pip install simple`, and the corresponding
first response is that the state of installed packages is `simple 0.2.0`.
Note that by default the highest version of an available package will be
installed.

The second request is to uninstall simple again, which will result in the
state `null` (basically an empty list of installed packages).

When the yaml tests are run, each response is verified by checking which
packages got actually installed.  Note that this is check is done in
alphabetical order.



The linter is very useful for initally checking `.yml` files, e.g.:

    $ python linter.py -v simple.yml

To run only the yaml tests, use (from the root of the source tree):

    $ tox -e py38 -- -m yaml -vv

Or, in order to avoid collecting all the test cases:

    $ tox -e py38 -- tests/functional/test_yaml.py

Or, only a specific test:

    $ tox -e py38 -- tests/functional/test_yaml.py -k simple

Or, just a specific test case:

    $ tox -e py38 -- tests/functional/test_yaml.py -k simple-0


<!-- TODO: Add a good description of the format and how it can be used. -->
