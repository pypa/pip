.. note::

    This section of the documentation is currently being written. pip
    developers welcome your help to complete this documentation. If
    you're interested in helping out, please let us know in the
    `tracking issue <https://github.com/pypa/pip/issues/6583>`__, or
    just submit a pull request and mention it in that tracking issue.

============
Issue Triage
============

This serves as an introduction to issue tracking in pip as well as
how to help triage reported issues.


Issue Tracker
=============

The `pip issue tracker <https://github.com/pypa/pip/issues>`__ is hosted on
GitHub alongside the project.

Currently, the issue tracker is used for bugs, feature requests, and general
user support.

In the pip issue tracker, we make use of labels and milestones to organize and
track work.

Labels
------

Issue labels are used to:

#. Categorize issues
#. Provide status information for contributors and reporters
#. Help contributors find tasks to work on

The current set of labels are divided into several categories identified by
prefix:

**C - Category**
  which area of ``pip`` functionality a feature request or issue is related to

**K - Kind**

**O - Operating System**
  for issues that are OS-specific

**P - Project/Platform**
  related to something external to ``pip``

**R - Resolution**
  no more discussion is really needed, an action has been identified and the
  issue is waiting or closed

**S - State**
  for some automatic labels and other indicators that work is needed

**type**
  the role or flavor of an issue

The specific labels falling into each category have a description that can be
seen on the `Labels <https://github.com/pypa/pip/labels>`__ page.

In addition, there are several standalone labels:

**good first issue**
  this label marks an issue as beginner-friendly and shows up in banners that
  GitHub displays for first-time visitors to the repository

**triage**
  default label given to issues when they are created

**trivial**
  special label for pull requests that removes the
  :ref:`news file requirement <choosing-news-entry-type>`

**needs rebase or merge**
  this is a special label used by BrownTruck to mark PRs that have merge
  conflicts

Automation
----------

There are several helpers to manage issues and pull requests.

Issues created on the issue tracker are automatically given the
``triage`` label by the
`triage-new-issues <https://github.com/apps/triage-new-issues>`__
bot. The label is automatically removed when another label is added.

When an issue needs feedback from the author we can label it with
``S: awaiting response``. When the author responds, the
`no-response <https://github.com/apps/no-response>`__ bot removes the label.

After an issue has been closed for 30 days, the
`lock <https://github.com/apps/lock>`__ bot locks the issue and adds the
``S: auto-locked`` label. This allows us to avoid monitoring existing closed
issues, but unfortunately prevents and references to issues from showing up as
links on the closed issue.


Triage Issues
=============

Users can make issues for a number of reasons:

#. Suggestions about pip features that could be added or improved
#. Problems using pip
#. Concerns about pip usability
#. General packaging problems to be solved with pip
#. Problems installing or using Python packages
#. Problems managing virtual environments
#. Problems managing Python installations

To triage issues means to identify what kind of issue is happening and

* confirm bugs
* provide support
* discuss and design around the uses of the tool

Specifically, to address an issue:

#. Read issue title
#. Scan issue description
#. Ask questions
#. If time is available, try to reproduce
#. Search for or remember related issues and link to them
#. Identify an appropriate area of concern (if applicable)

Keep in mind that all communication is happening with other people and
should be done with respect per the
`Code of Conduct <https://www.pypa.io/en/latest/code-of-conduct/>`__.

The lifecycle of an issue (bug or support) generally looks like:

#. waiting for triage (marked with label ``triage``)
#. confirming issue - some discussion with the user, gathering
   details, trying to reproduce the issue (may be marked with a specific
   category, ``S: awaiting-respose``, ``S: discussion-needed``, or
   ``S: need-repro``)
#. confirmed - the issue is pretty consistently reproducible in a
   straightforward way, or a mechanism that could be causing the issue has been
   identified
#. awaiting fix - the fix is identified and no real discussion on the issue
   is needed, should be marked ``R: awaiting PR``
#. closed - can be for several reasons

   * fixed
   * could not be reproduced, no more details could be obtained, and no
     progress can be made
   * actual issue was with another project or related to system
     configuration and pip cannot (or will not) be adapted for it


Requesting information
----------------------

Requesting more information to better understand the context and environment
that led to the issue. Examples of specific information that may be useful
depending on the situation:

* pip debug: ``pip debug``
* pip version: ``pip -V``
* Python version: ``python -VV``
* Python path: ``python -c 'import sys; print(sys.executable)'``
* ``python`` on ``PATH``: Unix: ``which python``; Windows: ``where python``
* Python as resolved by the shell: ``type python``
* Origin of pip (get-pip.py, OS-level package manager, ensurepip, manual
  installation)
* Using a virtual environment (with ``--system-site-packages``?)
* Using a conda environment
* ``PATH`` environment variable
* Network situation (e.g. airgapped environment, firewalls)
* ``--verbose`` output of a failing command
* (Unix) ``strace`` output from a failing command (be careful not to output
  into the same directory as a package that's being installed, otherwise pip
  will loop forever copying the log file...)
* (Windows)
  `procmon <https://docs.microsoft.com/en-us/sysinternals/downloads/procmon>`__
  output during a failing command
  (`example request <https://github.com/pypa/pip/issues/6814#issuecomment-516611389>`__)
* Listing of files relevant to the issue (e.g. ``ls -l venv/lib/pythonX.Y/problem-package.dist-info/``)
* whether the unexpected behavior ever worked as expected - if so then what
  were the details of the setup (same information as above)


Generally, information is good to request if it can help confirm or rule out
possible sources of error. We shouldn't request information that does not
improve our understanding of the situation.


Reproducing issues
------------------

Whenever an issue happens and the cause isn't obvious, it is important
that we be able to reproduce it independently. This serves several purposes:

#. If it is a pip bug, then any fix will need tests - a good reproducer
   is most of the way towards that.
#. If it is not reproducible using the provided instructions, that helps
   rule out a lot of possible causes.
#. A clear set of instructions is an easy way to get on the same page as
   someone reporting an issue.

The best way to reproduce an issue is with a script.

A script can be copied into a file and executed, whereas shell output
has to be manually copied a line at a time.

Scripts to reproduce issues should be:

- portable (few/no assumptions about the system, other that it being Unix or Windows as applicable)
- non-destructive
- convenient
- require little/no setup on the part of the runner

Examples:

- creating and installing multiple wheels with different versions
  (`link <https://github.com/pypa/pip/issues/4331#issuecomment-520156471>`__)
- using a small web server for authentication errors
  (`link <https://github.com/pypa/pip/issues/2920#issuecomment-508953118>`__)
- using docker to test system or global configuration-related issues
  (`link <https://github.com/pypa/pip/issues/5533#issuecomment-520159896>`__)
- using docker to test special filesystem permission/configurations
  (`link <https://github.com/pypa/pip/issues/6364#issuecomment-507074729>`__)
- using docker for global installation with get-pip
  (`link <https://github.com/pypa/pip/issues/6498#issuecomment-513501112>`__)
- get-pip on system with no ``/usr/lib64``
  (`link <https://github.com/pypa/pip/issues/5379#issuecomment-515270576>`__)
- reproducing with ``pip`` from current development branch
  (`link <https://github.com/pypa/pip/issues/6707#issue-467770959>`__)


Reaching resolution
-------------------

Some user support questions are more related to system configuration than pip.
It's important to treat these issues with the same care and attention as
others, specifically:

#. Unless the issue is very old and the user doesn't seem active, wait for
   confirmation before closing the issue
#. Direct the user to the most appropriate forum for their questions:

   * For Ubuntu, `askubuntu <https://askubuntu.com/>`__
   * For Other linuxes/unixes, `serverfault <https://serverfault.com/>`__
   * For network connectivity issues,
     `serverfault <https://serverfault.com/>`__

#. Just because a user support question is best solved using some other forum
   doesn't mean that we can't make things easier. Try to extract and
   understand from the user query how things could have been made easier for
   them or you, for example with better warning or error messages. If an issue
   does not exist covering that case then create one. If an issue does exist then
   make sure to reference that issue before closing this one.
#. A user may be having trouble installing a package, where the package
   ``setup.py`` or build-backend configuration is non-trivial. In these cases we
   can help to troubleshoot but the best advice is going to be to direct them
   to the support channels for the related projects.
#. Do not be hasty to assume it is one cause or another. What looks like
   someone else's problem may still be an issue in pip or at least something
   that could be improved.
#. For general discussion on Python packaging:

   * `pypa/packaging <https://github.com/pypa/packaging-problems>`__
   * `discuss.python.org/packaging <https://discuss.python.org/c/packaging>`__


Closing issues
--------------

An issue may be considered resolved and closed when:

- for each possible improvement or problem represented in the issue
  discussion:

  - Consensus has been reached on a specific action and the actions
    appear to be external to the project, with no follow up needed
    in the project afterwards.

    - PEP updates (with a corresponding issue in
      `python/peps <https://github.com/python/peps>`__)
    - already tracked by another issue

  - A project-specific issue has been identified and the issue no
    longer occurs as of the latest commit on the main branch.

- An enhancement or feature request no longer has a proponent and the maintainers
  don't think it's worth keeping open.
- An issue has been identified as a duplicate, and it is clearly a duplicate (i.e. the
  original report was very good and points directly to the issue)
- The issue has been fixed, and can be independently validated as no longer being an
  issue. If this is with code then the specific change/PR that led to it should be
  identified and posted for tracking.


Common issues
=============

#. network-related issues - any issue involving retries, address lookup, or
   anything like that are typically network issues.
#. issues related to having multiple Python versions, or an OS package
   manager-managed pip/python installation (specifically with Debian/Ubuntu).
   These typically present themselves as:

   #. Not being able to find installed packages
   #. basic libraries not able to be found, fundamental OS components missing
   #. In these situations you will want to make sure that we know how they got
      their Python and pip. Knowing the relevant package manager commands can
      help, e.g. ``dpkg -S``.
