===========
Development
===========

Pull Requests
=============

Submit Pull Requests against the `develop` branch.

Provide a good description of what you're doing and why.

Provide tests that cover your changes and try to run the tests locally first.

Automated Testing
=================

All pull requests and merges to 'develop' branch are tested in `Travis <https://travis-ci.org/>`_
based on our `.travis.yml file <https://github.com/pypa/pip/blob/develop/.travis.yml>`_.

Usually, a link to your specific travis build appears in pull requests, but if not,
you can find it on our `travis pull requests page <https://travis-ci.org/pypa/pip/pull_requests>`_

The only way to trigger Travis to run again for a pull request, is to submit another change to the pull branch.

We also have Jenkins CI that runs regularly for certain python versions on windows and centos.

Running tests
=============

OS Requirements: subversion, bazaar, git, and mercurial.

Python Requirements: nose, virtualenv, scripttest, and mock

Ways to run the tests locally:

::

 $ python setup.py test  # Using the setuptools test plugin
 $ nosetests             # Using nosetests directly
 $ tox                   # Using tox against pip's tox.ini


Getting Involved
================

The pip project welcomes help in the following ways:

- Making Pull Requests for code, tests, or docs.
- Commenting on open issues and pull requests.
- Helping to answer questions on the mailing list.

If you want to become an official maintainer, start by helping out.

Later, when you think you're ready, get in touch with one of the maintainers,
and they will initiate a vote.

Release Process
===============

This process includes virtualenv, since pip releases necessitate a virtualenv release.

:<oldp>/<newp>: refers to the old and new versions of pip.
:<oldv>/<newv>: refers to the old and new versions of virtualenv.

1. Upgrade distribute, if needed:

 #. Upgrade distribute in ``virtualenv:develop`` using the :ref:`Refresh virtualenv` process.
 #. Create a pull request against ``pip:develop`` with a modified ``.travis.yml`` file that installs virtualenv from ``virtualenv:develop``, to confirm the travis builds are still passing.

2. Create Release branches:

 #. Create ``pip:<newp>`` branch.
 #. In ``pip:develop``, change ``pip.version`` to '<newp>.post1'.
 #. Create ``virtualenv:<newv>`` branch.
 #. In ``virtualenv:develop``, change ``virtualenv.version`` to '<newv>.post1'.

3. Prepare "rcX":

 #. In ``pip:<newp>``, change ``pip.version`` to '<newp>rcX', and tag with '<newp>rcX'.
 #. Build a pip sdist from ``pip:<newp>``, and build it into ``virtualenv:<newv>`` using the :ref:`Refresh virtualenv` process.
 #. In ``virtualenv:<newv>``, change ``virtualenv.version`` to '<newv>rcX', and tag with '<newv>rcX'.

4. Announce ``pip-<newp>rcX`` and ``virtualenv-<newv>rcX`` with the :ref:`RC Install Instructions` and elicit feedback.

5. Apply fixes to 'rcX':

 #. Apply fixes to ``pip:<newp>`` and ``virtualenv:<newv>``
 #. Periodically merge fixes to ``pip:develop`` and ``virtualenv:develop``

6. Repeat #4 thru #6 if needed.

7. Final Release:

 #. In ``pip:<newp>``, change ``pip.version`` to '<newp>', and tag with '<newp>'.
 #. Merge ``pip:<newp>`` to ``pip:master``.
 #. Build a pip sdist from ``pip:<newp>``, and load it into ``virtualenv:<newv>`` using the :ref:`Refresh virtualenv` process.
 #. Merge ``vitualenv:<newv>`` to ``virtualenv:develop``.
 #. In ``virtualenv:<newv>``, change ``virtualenv.version`` to '<newv>', and tag with '<newv>'.
 #. Merge ``virtualenv:<newp>`` to ``virtualenv:master``
 #. Build and upload pip and virtualenv sdists to PyPI.

.. _`Refresh virtualenv`:

Refresh virtualenv
++++++++++++++++++

#. Set the embedded versions of pip, distribute and setuptools in ``bin/refresh-support-files.py``
#. Additionally, set the version of distribute in ``virtualenv_embedded/distribute_setup.py``, and setuptools in ``virtualenv_embedded/ez_setup.py``
#. Run ``bin/refresh-support-files.py`` to download the latest versions.
   When specifying a beta of pip not on pypi, the last part of this script will fail. In this case, the pip sdist needs to be placed manually into ``virtualenv_support``.
#. Run ``bin/rebuild-script.py`` to rebuild virtualenv based on the latest versions.


.. _`RC Install Instructions`:

RC Install Instructions
+++++++++++++++++++++++

#. Download and unpack ``https://github.com/pypa/virtualenv/archive/<newv>rcX.tar.gz``
#. Run: ``python virtualenv-<newv>rcX/virtualenv.py myVE``
#. ``myVE/bin/pip`` will be the <newp>rcX version of pip.
