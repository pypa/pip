:orphan:

Dependency Links
================

In pip 1.5 processing dependency links was deprecated and it was removed
completely in pip 1.6. Dependency links supports a few different scenarios.


Depending on a Fork of a Project
--------------------------------

If you need to depend on a forked version of a project and it is for your own
personal use, than you can simply use a requirements.txt file that points to
the fork.

.. code::

    # We need this fork instead of the foobar that exists on PyPI
    git+https://github.com/example/foobar.git#egg=foobar

    myproject==1.0  # myproject has a setup.py dependency on foobar

If you need to depend on a forked version of a project for something you want
to distribute to other people than you should rename the project and upload
it with a new name to PyPI. This way people can depend and install on it
normally.

Deploying Directly from VCS
---------------------------

If you're using dependency_links to essentially deploy a tree of dependencies
directly from VCS then you have two primary options. You can either setup
a requirements.txt that lists all of the repositories such as:

.. code::

    # These are the locations of the git repos
    git+https://github.com/example/foobar.git#egg=foobar
    git+https://github.com/example/super.git#egg=super
    git+https://github.com/example/duper.git#egg=duper

    # This is my main package
    myproject==1.0  # This depends on foobar, super, and duper from git repos

Or you can setup a private package index and point pip to use it instead. This
can be as simple as a directory full of packages exposed using Apache2 or Nginx
with an auto index, or can be as complex as a full blown index using software
such as `devpi <http://devpi.net/>`_.

If you're using a simple autoindex, then you can add it to pip using:

.. code:: console

    $ pip install --find-links https://example.com/deploy/ myproject

Or if you're using a full blown index it could be:

.. code:: console

    # Replace PyPI with the custom index
    $ pip install --index-url https://example.com/simple/ myproject
    # Add a custom index in addition to PyPI
    $ pip install --extra-index-url https://example.com/simple/ myproject
