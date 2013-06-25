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

As an example, the instructions assume we're releasing pip-1.4, and virtualenv-1.10.

1. Upgrade setuptools, if needed:

 #. Upgrade setuptools in ``virtualenv/develop`` using the :ref:`Refresh virtualenv` process.
 #. Create a pull request against ``pip/develop`` with a modified ``.travis.yml`` file that installs virtualenv from ``virtualenv/develop``, to confirm the travis builds are still passing.

2. Create Release branches:

 #. Create ``pip/release-1.4`` branch.
 #. In ``pip/develop``, change ``pip.version`` to '1.5.dev1'.
 #. Create ``virtualenv/release-1.10`` branch.
 #. In ``virtualenv/develop``, change ``virtualenv.version`` to '1.11.dev1'.

3. Prepare "rcX":

 #. In ``pip/release-1.4``, change ``pip.version`` to '1.4rcX', and tag with '1.4rcX'.
 #. Build a pip sdist from ``pip/release-1.4``, and build it into ``virtualenv/release-1.10`` using the :ref:`Refresh virtualenv` process.
 #. In ``virtualenv/release-1.10``, change ``virtualenv.version`` to '1.10rcX', and tag with '1.10rcX'.

4. Announce ``pip-1.4rcX`` and ``virtualenv-1.10rcX`` with the :ref:`RC Install Instructions` and elicit feedback.

5. Apply fixes to 'rcX':

 #. Apply fixes to ``pip/release-1.4`` and ``virtualenv/release-1.10``
 #. Periodically merge fixes to ``pip/develop`` and ``virtualenv/develop``

6. Repeat #4 thru #6 if needed.

7. Final Release:

 #. In ``pip/release-1.4``, change ``pip.version`` to '1.4', and tag with '1.4'.
 #. Merge ``pip/release-1.4`` to ``pip/master``.
 #. Build a pip sdist from ``pip/release-1.4``, and load it into ``virtualenv/release-1.10`` using the :ref:`Refresh virtualenv` process.
 #. Merge ``vitualenv/release-1.10`` to ``virtualenv/develop``.
 #. In ``virtualenv/release-1.10``, change ``virtualenv.version`` to '1.10', and tag with '1.10'.
 #. Merge ``virtualenv/release-1.10`` to ``virtualenv/master``
 #. Build and upload pip and virtualenv sdists to PyPI.

.. _`Refresh virtualenv`:

Refresh virtualenv
++++++++++++++++++

#. Update the embedded versions of pip and setuptools in ``virtualenv_support``.
#. Run ``bin/rebuild-script.py`` to rebuild virtualenv based on the latest versions.


.. _`RC Install Instructions`:

RC Install Instructions
+++++++++++++++++++++++

::

 $ curl -L -O https://github.com/pypa/virtualenv/archive/1.10rc1.tar.gz
 $ echo "<md5sum value>  1.10rc1.tar.gz" | md5sum -c
 1.10rc1.tar.gz: OK
 $ tar zxf 1.10rc1.tar.gz
 $ python virtualenv-1.10rc1/virtualenv.py myVE
 $ myVE/bin/pip install SomePackage

