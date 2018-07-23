=====================
pip's release process
=====================


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

Creating a new release
----------------------

#. On the current pip ``master`` branch, generate a new ``AUTHORS.txt`` by
   running ``invoke generate.authors`` and commit the results.
#. On the current pip ``master`` branch, make a new commit which bumps the
   version in ``pip/__init__.py`` to the release version and adjust the
   ``CHANGES.txt`` file to reflect the current date. The release version should
   follow a YY.N scheme, where YY is the two digit year, and N is the Nth
   release within that year.
#. On the current pip ``master`` branch, generate a new ``NEWS.rst`` by running
   ``invoke generate.news`` and commit the results.
#. Create a signed tag of the ``master`` branch of the form ``YY.N`` using the
   command ``git tag -s YY.N``.
#. Checkout the tag using ``git checkout YY.N`` and create the distribution
   files using ``python setup.py sdist bdist_wheel``.
#. Upload the distribution files to PyPI using twine
   (``twine upload -s dist/*``). The upload should include GPG signatures of
   the distribution files.
#. Push all of the changes.
#. Regenerate the ``get-pip.py`` script by running
   ``invoke generate.installer`` in the get-pip repository, and committing the
   results.

Creating a bug-fix release
--------------------------

Sometimes we need to release a bugfix release of the form ``YY.N.Z+1``. In
order to create one of these the changes should already be merged into the
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
