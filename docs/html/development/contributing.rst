============
Contributing
============

.. todo
   Create a "guide" to pip's internals and link to it from here saying
   "you might want to take a look at the guide"


Submitting Pull Requests
========================

Submit pull requests against the ``master`` branch, providing a good
description of what you're doing and why. You must have legal permission to
distribute any code you contribute to pip and it must be available under the
MIT License.

Provide tests that cover your changes and run the tests locally first. pip
:ref:`supports <compatibility-requirements>` multiple Python versions and
operating systems. Any pull request must consider and work on all these
platforms.

Pull Requests should be small to facilitate easier review. Keep them
self-contained, and limited in scope. `Studies have shown`_ that review quality
falls off as patch size grows. Sometimes this will result in many small PRs to
land a single large feature. In particular, pull requests must not be treated
as "feature branches", with ongoing development work happening within the PR.
Instead, the feature should be broken up into smaller, independent parts which
can be reviewed and merged individually.

Additionally, avoid including "cosmetic" changes to code that
is unrelated to your change, as these make reviewing the PR more difficult.
Examples include re-flowing text in comments or documentation, or addition or
removal of blank lines or whitespace within lines. Such changes can be made
separately, as a "formatting cleanup" PR, if needed.

Automated Testing
=================

All pull requests and merges to 'master' branch are tested using `Travis CI`_
and `Appveyor CI`_ based on our `.travis.yml`_ and `.appveyor.yml`_ files.

You can find the status and results to the CI runs for your PR on GitHub's Web
UI for the pull request. You can also find links to the CI services' pages for
the specific builds in the form of "Details" links, in case the CI run fails
and you wish to view the output.

To trigger CI to run again for a pull request, you can close and open the pull
request or submit another change to the pull request. If needed, project
maintainers can manually trigger a restart of a job/build.


NEWS Entries
============

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

Contents of a NEWS entry
------------------------

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

Choosing the type of NEWS entry
-------------------------------

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


Updating your branch
====================

As you work, you might need to update your local master branch up-to-date with
the ``master`` branch in the main pip repository, which moves forward as the
maintainers merge pull requests. Most people working on the project use the
following workflow.

This assumes that you have Git configured so that when you run the following
command:

.. code-block:: console

    git remote -v

Your output looks like this:

.. code-block:: console

    origin  https://github.com/USERNAME/pip.git (fetch)
    origin  https://github.com/USERNAME/pip.git (push)
    upstream  https://github.com/pypa/pip.git (fetch)
    upstream  https://github.com/pypa/pip.git (push)

In the example above, ``USERNAME`` is your username on GitHub.

First, fetch the latest changes from the main pip repository, ``upstream``:

.. code-block:: console

    git fetch upstream

Then, check out your local ``master`` branch, and rebase the changes on top of
it:

.. code-block:: console

    git checkout master
    git rebase upstream/master

At this point, you might have to `resolve merge conflicts`_. Once this is done,
push the updates you have just made to your local ``master`` branch to your
``origin`` repository on GitHub:

.. code-block:: console

    git checkout master
    git push origin master

Now your local ``master`` branch and the ``master`` branch in your ``origin``
repo have been updated with the most recent changes from the main pip
repository.

To keep your branches updated, the process is similar:

.. code-block:: console

    git checkout awesome-feature
    git fetch upstream
    git rebase upstream/master

Now your branch has been updated with the latest changes from the
``master`` branch on the upstream pip repository.

It's good practice to back up your branches by pushing them to your
``origin`` on GitHub as you are working on them. To push a branch,
run this command:

.. code-block:: console

    git push origin awesome-feature

In this example, ``<awesome-feature>`` is the name of your branch. This
will push the branch you are working on to GitHub, but will not
create a PR.

Once you have pushed your branch to your ``origin``, if you need to
update it again, you will have to force push your changes by running the
following command:

.. code-block:: console

    git push -f origin awesome-feature

The ``-f`` (or ``--force``) flag after ``push`` forces updates from your local
branch to update your ``origin`` branch. If you have a PR open on your
branch, force pushing will update your PR. (This is a useful command
when someone requests changes on a PR.)

If you get an error message like this:

.. code-block:: console

    ! [rejected]        awesome-feature -> awesome-feature (non-fast-forward)
    error: failed to push some refs to 'https://github.com/USERNAME/pip.git'
    hint: Updates were rejected because the tip of your current branch is behind
    hint: its remote counterpart. Integrate the remote changes (e.g.
    hint: 'git pull ...') before pushing again.
    hint: See the 'Note about fast-forwards' in 'git push --help' for details.

Try force-pushing your branch with ``push -f``.

The ``master`` branch in the main pip repository gets updated frequently, so
you might have to update your branch at least once while you are working on it.


Becoming a maintainer
=====================

If you want to become an official maintainer, start by helping out.

Later, when you think you're ready, get in touch with one of the maintainers
and they will initiate a vote.

.. note::

    Upon becoming a maintainer, a person should be given access to various
    pip-related tooling across multiple platforms. These are noted here for
    future reference by the maintainers:

    - GitHub Push Access
    - PyPI Publishing Access
    - CI Administration capabilities
    - ReadTheDocs Administration capabilities

.. _`Studies have shown`: https://smartbear.com/smartbear/media/pdfs/wp-cc-11-best-practices-of-peer-code-review.pdf
.. _`resolve merge conflicts`: https://help.github.com/articles/resolving-a-merge-conflict-using-the-command-line/
.. _`Travis CI`: https://travis-ci.org/
.. _`Appveyor CI`: https://www.appveyor.com/
.. _`.travis.yml`: https://github.com/pypa/pip/blob/master/.travis.yml
.. _`.appveyor.yml`: https://github.com/pypa/pip/blob/master/.appveyor.yml
.. _`towncrier`: https://pypi.org/project/towncrier/
