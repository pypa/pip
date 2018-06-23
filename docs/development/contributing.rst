===================
Contributing to pip
===================

.. todo
   Create a "guide" to pip's internals and link to it from here saying
   "you might want to take a look at the guide"


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


Becoming a maintainer
=====================

If you want to become an official maintainer, start by helping out.

Later, when you think you're ready, get in touch with one of the maintainers
and they will initiate a vote.

.. _`Travis CI`: https://travis-ci.org/
.. _`Appveyor CI`: https://www.appveyor.com/
.. _`.travis.yml`: https://github.com/pypa/pip/blob/master/.travis.yml
.. _`appveyor.yml`: https://github.com/pypa/pip/blob/master/appveyor.yml
.. _`towncrier`: https://pypi.org/project/towncrier/
