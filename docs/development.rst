===========
Development
===========

Pull Requests
=============

- Submit Pull Requests against the `master` branch.
- Provide a good description of what you're doing and why.
- Provide tests that cover your changes and try to run the tests locally first.

**Example**. Assuming you set up GitHub account, forked pip repository from
https://github.com/pypa/pip to your own page via web interface, and your
fork is located at https://github.com/yourname/pip

::

  $ git clone git@github.com:pypa/pip.git
  $ cd pip
  # ...
  $ git diff
  $ git add <modified> ...
  $ git status
  $ git commit

You may reference relevant issues in commit messages (like #1259) to
make GitHub link issues and commits together, and with phrase like
"fixes #1259" you can even close relevant issues automatically. Now
push the changes to your fork::

  $ git push git@github.com:yourname/pip.git

Open Pull Requests page at https://github.com/yourname/pip/pulls and
click "New pull request". That's it.


Automated Testing
=================

All pull requests and merges to 'master' branch are tested in `Travis <https://travis-ci.org/>`_
based on our `.travis.yml file <https://github.com/pypa/pip/blob/master/.travis.yml>`_.

Usually, a link to your specific travis build appears in pull requests, but if not,
you can find it on our `travis pull requests page <https://travis-ci.org/pypa/pip/pull_requests>`_

The only way to trigger Travis to run again for a pull request, is to submit another change to the pull branch.

We also have Jenkins CI that runs regularly for certain python versions on windows and centos.

Running tests
=============

OS Requirements: subversion, bazaar, git, and mercurial.

Python Requirements: tox or pytest, virtualenv, scripttest, and mock

Ways to run the tests locally:

::

 $ tox -e py33           # The preferred way to run the tests, can use pyNN to
                         # run for a particular version or leave off the -e to
                         # run for all versions.
 $ python setup.py test  # Using the setuptools test plugin
 $ py.test               # Using py.test directly
 $ tox                   # Using tox against pip's tox.ini

If you are missing one of the VCS tools, you can tell ``py.test`` to skip it:

::

 $ py.test -k 'not bzr'
 $ py.test -k 'not svn'


Getting Involved
================

The pip project welcomes help in the following ways:

- Making Pull Requests for code, tests, or docs.
- Commenting on open issues and pull requests.
- Helping to answer questions on the `mailing list`_.

If you want to become an official maintainer, start by helping out.

Later, when you think you're ready, get in touch with one of the maintainers,
and they will initiate a vote.


Adding a NEWS Entry
===================

The ``NEWS.rst`` file is managed using
`towncrier <https://pypi.org/project/towncrier/>`_ and all non trivial changes
must be accompanied by a news entry.

To add an entry to the news file, first you need to have created an issue
describing the change you want to make. A Pull Request itself *may* function as
such, but it is preferred to have a dedicated issue (for example, in case the
PR ends up rejected due to code quality reasons).

Once you have an issue or pull request, you take the number and you create a
file inside of the ``news/`` directory named after that issue number with an
extension of ``removal``, ``feature``, ``bugfix``, or ``doc``. Thus if your
issue or PR number is ``1234`` and this change is fixing a bug, then you would
create a file ``news/1234.bugfix``. PRs can span multiple categories by creating
multiple files (for instance, if you added a feature and deprecated/removed the
old feature at the same time, you would create ``news/NNNN.feature`` and
``news/NNNN.removal``). Likewise if a PR touches multiple issues/PRs you may
create a file for each of them with the exact same contents and Towncrier will
deduplicate them.

The contents of this file are reStructuredText formatted text that will be used
as the content of the news file entry. You do not need to reference the issue
or PR numbers here as towncrier will automatically add a reference to all of
the affected issues when rendering the news file.

A trivial change is anything that does not warrant an entry in the news file.
Some examples are: Code refactors that don't change anything as far as the
public is concerned, typo fixes, white space modification, etc. To mark a PR
as trivial a contributor simply needs to add a randomly named, empty file to the
``news/`` directory with the extension of ``.trivial``. If you are on a POSIX
like operating system, one can be added by running
``touch news/$(uuidgen).trivial``. Core committers may also add a "trivial"
label to the PR which will accomplish the same thing.

Upgrading, removing, or adding a new vendored library gets a special mention
using a ``news/<library>.vendor`` file. This is in addition to any features,
bugfixes, or other kinds of news that pulling in this library may have. This
uses the library name as the key so that updating the same library twice doesn't
produce two news file entries.


Release Process
===============

#. On the current pip ``master`` branch, generate a new ``AUTHORS.txt`` by
   running ``invoke generate.authors`` and commit the results.
#. On the current pip ``master`` branch, make a new commit which bumps the
   version in ``pip/__init__.py`` to the release version and adjust the
   ``CHANGES.txt`` file to reflect the current date.
#. On the current pip ``master`` branch, generate a new ``NEWS.rst`` by running
   ``invoke generate.news`` and commit the results.
#. Create a signed tag of the ``master`` branch of the form ``X.Y.Z`` using the
   command ``git tag -s X.Y.Z``.
#. Checkout the tag using ``git checkout X.Y.Z`` and create the distribution
   files using ``python setup.py sdist bdist_wheel``.
#. Upload the distribution files to PyPI using twine
   (``twine upload -s dist/*``). The upload should include GPG signatures of
   the distribution files.
#. Push all of the changes.
#. Regenerate the ``get-pip.py`` script by running
   ``invoke generate.installer`` in the get-pip repository, and committing the
   results.


Creating a Bugfix Release
=========================

Sometimes we need to release a bugfix release of the form ``X.Y.Z+1``. In order
to create one of these the changes should already be merged into the
``master`` branch.

#. Create a new ``release/X.Y.Z+1`` branch off of the ``X.Y.Z`` tag using the
   command ``git checkout -b release/X.Y.Z+1 X.Y.Z``.
#. Cherry pick the fixed commits off of the ``master`` branch, fixing any
   conflicts and moving any changelog entries from the development version's
   changelog section to the ``X.Y.Z+1`` section.
#. Push the ``release/X.Y.Z+1`` branch to github and submit a PR for it against
   the ``master`` branch and wait for the tests to run.
#. Once tests run, merge the ``release/X.Y.Z+1`` branch into master, and follow
   the above release process starting with step 4.


.. _`mailing list`: https://mail.python.org/mailman/listinfo/distutils-sig
