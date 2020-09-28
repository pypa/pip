===============
Release process
===============

.. _`Release Cadence`:

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
3 months later.

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

.. _`Deprecation Policy`:

Deprecation Policy
==================

Any change to pip that removes or significantly alters user-visible behavior
that is described in the pip documentation will be deprecated for a minimum of
6 months before the change occurs.

Certain changes may be fast tracked and have a deprecation period of 3 months.
This requires at least two members of the pip team to be in favor of doing so,
and no pip maintainers opposing.

Deprecation will take the form of a warning being issued by pip when the
feature is used. Longer deprecation periods, or deprecation warnings for
behavior changes that would not normally be covered by this policy, are also
possible depending on circumstances, but this is at the discretion of the pip
maintainers.

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

Python 2 Support
----------------

pip will continue to ensure that it runs on Python 2.7 after the CPython 2.7
EOL date. Support for Python 2.7 will be dropped, if bugs in Python 2.7 itself
make this necessary (which is unlikely) or in pip 21.0 (Jan 2021), whichever is
earlier.

However, bugs reported with pip which only occur on Python 2.7 would likely not
be addressed directly by pip's maintainers. Pull Requests to fix Python 2.7
only bugs will be considered, and merged (subject to normal review processes).
Note that there may be delays due to the lack of developer resources for
reviewing such pull requests.

Python Support Policy
---------------------

In general, a given Python version is supported until its usage on PyPI falls below 5%.
This is at the maintainers' discretion, in case extraordinary circumstances arise.

.. _`Feature Flags`:

Feature Flags
=============

``--use-deprecated``
--------------------

Example: ``--use-deprecated=legacy-resolver``

Use for features that will be deprecated. Deprecated features should remain
available behind this flag for at least six months, as per the deprecation
policy.

Features moved behind this flag should always include a warning that indicates
when the feature is scheduled to be removed.

Once the feature is removed, users who use the flag should be shown an error.

``--use-feature``
-----------------

Example: ``--use-feature=2020-resolver``

Use for new features that users can test before they become pip's default
behaviour (e.g. alpha or beta releases).

Once the feature becomes the default behaviour, this flag can remain in place,
but should issue a warning telling the user that it is no longer necessary.

Release Process
===============

Creating a new release
----------------------

#. Checkout the current pip ``master`` branch.
#. Ensure you have the latest ``nox`` installed.
#. Prepare for release using ``nox -s prepare-release -- YY.N``.
   This will update the relevant files and tag the correct commit.
#. Build the release artifacts using ``nox -s build-release -- YY.N``.
   This will checkout the tag, generate the distribution files to be
   uploaded and checkout the master branch again.
#. Upload the release to PyPI using ``nox -s upload-release -- YY.N``.
#. Push all of the changes including the tag.
#. Regenerate the ``get-pip.py`` script in the `get-pip repository`_ (as
   documented there) and commit the results.
#. Submit a Pull Request to `CPython`_ adding the new version of pip (and upgrading
   setuptools) to ``Lib/ensurepip/_bundled``, removing the existing version, and
   adjusting the versions listed in ``Lib/ensurepip/__init__.py``.


.. note::

  If the release dropped the support of an obsolete Python version ``M.m``,
  a new ``M.m/get-pip.py`` needs to be published: update the ``all`` task from
  ``tasks/generate.py`` in `get-pip repository`_ and make a pull request to
  `psf-salt repository`_ to add the new ``get-pip.py`` (and its directory) to
  ``salt/pypa/bootstrap/init.sls``.


.. note::

  If the ``get-pip.py`` script needs to be updated due to changes in pip internals
  and if the last ``M.m/get-pip.py`` published still uses the default template, make
  sure to first duplicate ``templates/default.py`` as ``templates/pre-YY.N.py``
  before updating it and specify in ``tasks/generate.py`` that ``M.m/get-pip.py``
  now needs to use ``templates/pre-YY.N.py``.


Creating a bug-fix release
--------------------------

Sometimes we need to release a bugfix release of the form ``YY.N.Z+1``. In
order to create one of these the changes should already be merged into the
``master`` branch.

#. Create a new ``release/YY.N.Z+1`` branch off of the ``YY.N`` tag using the
   command ``git checkout -b release/YY.N.Z+1 YY.N``.
#. Cherry pick the fixed commits off of the ``master`` branch, fixing any
   conflicts.
#. Run ``nox -s prepare-release -- YY.N.Z+1``.
#. Merge master into your release branch and drop the news files that have been
   included in your release (otherwise they would also appear in the ``YY.N+1``
   changelog)
#. Push the ``release/YY.N.Z+1`` branch to github and submit a PR for it against
   the ``master`` branch and wait for the tests to run.
#. Once tests run, merge the ``release/YY.N.Z+1`` branch into master, and follow
   the above release process starting with step 4.

.. _`get-pip repository`: https://github.com/pypa/get-pip
.. _`psf-salt repository`: https://github.com/python/psf-salt
.. _`CPython`: https://github.com/python/cpython
