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
click "New pull request" and select your fork. That's it.

Pull requests should be self-contained, and limited in scope. Before being
merged, a pull request must be reviewed, and keeping individual PRs limited
in scope makes this far easier. In particular, pull requests must not be
treated as "feature branches", with ongoing development work happening
within the PR. Instead, the feature should be broken up into smaller,
independent parts which can be reviewed and merged individually.

When creating a pull request, avoid including "cosmetic" changes to
code that is unrelated to your change, as these make reviewing the PR
more difficult. Examples include re-flowing text in comments or
documentation, or addition or removal of blank lines or whitespace
within lines. Such changes can be made separately, as a "formatting
cleanup" PR, if needed.


Automated Testing
=================

All pull requests and merges to 'master' branch are tested using `Travis CI`_
and `Appveyor CI`_ based on our `.travis.yml`_ and `appveyor.yml`_ files.

You can find the status and results to the CI runs for your PR on GitHub's Web
UI for the pull request. You can also find links to the CI services' pages for
the specific builds in the form of "Details" links, in case the CI run fails
and you wish to view the output.

To trigger CI to run again for a pull request, you can close and open the pull
request or submit another change to the pull request. If needed, project
maintainers can manually trigger a restart of a job/build.

Running tests
=============

OS Requirements: subversion, bazaar, git, and mercurial.

Python Requirements: tox or install all packages listed in
`tools/tests-requirements.txt`_

Ways to run the tests locally::

 $ tox -e py36           # The preferred way to run the tests, can use pyNN to
                         # run for a particular version or leave off the -e to
                         # run for all versions.
 $ python setup.py test  # Using the setuptools test plugin
 $ py.test               # Using py.test directly
 $ tox                   # Using tox against pip's tox.ini

If you are missing one of the VCS tools, you can tell ``py.test`` to skip it::

 # When using tox
 $ tox -e py36 -- -k 'not svn'
 $ tox -e py36 -- -k 'not (svn or git)'
 # Directly with py.test
 $ py.test -k 'not svn'
 $ py.test -k 'not (svn or git)'


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

The ``NEWS.rst`` file is managed using `towncrier`_ and all non trivial changes
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

In order to maintain a consistent style in the ``NEWS.rst`` file, it is
preferred to keep the news entry to the point, in sentence case, shorter than
80 characters and in an imperative tone -- an entry should complete the sentence
"This change will ...". In rare cases, where one line is not enough, use a
summary line in an imperative tone followed by a blank line separating it
from a description of the feature/change in one or more paragraphs, each wrapped
at 80 characters. Remember that a news entry is meant for end users and should
only contain details relevant to an end user.

A trivial change is anything that does not warrant an entry in the news file.
Some examples are: Code refactors that don't change anything as far as the
public is concerned, typo fixes, white space modification, etc. To mark a PR
as trivial a contributor simply needs to add a randomly named, empty file to
the ``news/`` directory with the extension of ``.trivial``. If you are on a
POSIX like operating system, one can be added by running
``touch news/$(uuidgen).trivial``. On Windows, the same result can be achieved
in Powershell using ``New-Item "news/$([guid]::NewGuid()).trivial"``. Core
committers may also add a "trivial" label to the PR which will accomplish the
same thing.

Upgrading, removing, or adding a new vendored library gets a special mention
using a ``news/<library>.vendor`` file. This is in addition to any features,
bugfixes, or other kinds of news that pulling in this library may have. This
uses the library name as the key so that updating the same library twice doesn't
produce two news file entries.

Changes to the processes, policies, or other non code related changed that are
otherwise notable can be done using a ``news/<name>.process`` file. This is not
typically used, but can be used for things like changing version schemes,
updating deprecation policy, etc.


Release Cadence
===============

The pip project has a release cadence of releasing whatever is on ``master``
every 3 months. This gives users a predictable pattern for when releases
are going to happen and prevents locking up improvements for fixes for long
periods of time, while still preventing massively fracturing the user base
with version numbers.

Our release months are January, April, July, October. The release date within
that month will be up to the release manager for that release. If there are
no changes, then that release month is skipped and the next release will be
3 month later.

The release manager may, at their discretion, choose whether or not there
will be a pre-release period for a release, and if there is may extend that
period into the next month if needed.

Because releases are made direct from the ``master`` branch, it is essential
that ``master`` is always in a releasable state. It is acceptable to merge
PRs that partially implement a new feature, but only if the partially
implemented version is usable in that state (for example, with reduced
functionality or disabled by default). In the case where a merged PR is found
to need extra work before being released, the release manager always has the
option to back out the partial change prior to a release. The PR can then be
reworked and resubmitted for the next release.


Deprecation Policy
==================

Any change to pip that removes or significantly alters user-visible behavior
that is described in the pip documentation will be deprecated for a minimum of
6 months before the change occurs. Deprecation will take the form of a warning
being issued by pip when the feature is used. Longer deprecation periods, or
deprecation warnings for behavior changes that would not normally be covered by
this policy, are also possible depending on circumstances, but this is at the
discretion of the pip developers.

Note that the documentation is the sole reference for what counts as agreed
behavior. If something isn't explicitly mentioned in the documentation, it can
be changed without warning, or any deprecation period, in a pip release.
However, we are aware that the documentation isn't always complete - PRs that
document existing behavior with the intention of covering that behavior with
the above deprecation process are always acceptable, and will be considered on
their merits.

.. note::

  pip has a helper function for making deprecation easier for pip maintainers.
  The supporting documentation can be found in the source code of
  ``pip._internal.utils.deprecation.deprecated``. The function is not a part of
  pip's public API.

Release Process
===============

#. On the current pip ``master`` branch, generate a new ``AUTHORS.txt`` by
   running ``invoke generate.authors`` and commit the results.
#. On the current pip ``master`` branch, make a new commit which bumps the
   version in ``pip/__init__.py`` to the release version and adjust the
   ``CHANGES.txt`` file to reflect the current date. The release version should
   follow a YY.N scheme, where YY is the two digit year, and N is the Nth
   release within that year.
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

#. Create a new ``release/YY.N.Z+1`` branch off of the ``YY.N`` tag using the
   command ``git checkout -b release/YY.N.Z+1 YY.N``.
#. Cherry pick the fixed commits off of the ``master`` branch, fixing any
   conflicts and moving any changelog entries from the development version's
   changelog section to the ``YY.N.Z+1`` section.
#. Push the ``release/YY.N.Z+1`` branch to github and submit a PR for it against
   the ``master`` branch and wait for the tests to run.
#. Once tests run, merge the ``release/YY.N.Z+1`` branch into master, and follow
   the above release process starting with step 4.


.. _`mailing list`: https://mail.python.org/mailman/listinfo/distutils-sig
.. _`towncrier`: https://pypi.org/project/towncrier/
.. _`Travis CI`: https://travis-ci.org/
.. _`Appveyor CI`: https://www.appveyor.com/
.. _`.travis.yml`: https://github.com/pypa/pip/blob/master/.travis.yml
.. _`appveyor.yml`: https://github.com/pypa/pip/blob/master/appveyor.yml
.. _`Travis CI Pull Requests`: https://travis-ci.org/pypa/pip/pull_requests
.. _`tools/tests-requirements.txt`: https://github.com/pypa/pip/blob/master/tools/tests-requirements.txt
