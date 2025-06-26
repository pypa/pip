=============================================
Options that control the installation process
=============================================

When installing packages, pip chooses a distribution file, and
installs it in the user's environment. There are many choices (which
are `still evolving`_) involved in deciding which file to install, and
these are controlled by a variety of options.

.. note::

    This section of the documentation needs to be updated per
    :ref:`Resolver changes 2020`.

Controlling what gets installed
===============================

These options directly affect how the resolver uses the list of available
distribution files to decide which one to install. So these modify the
resolution algorithm itself, rather than the input to that algorithm.

``--upgrade``

Allow installing a newer version of an installed package. In principle, this
option actually affects "what gets considered", in the sense that it allows
the resolver to see other versions of installed packages. Without
``--upgrade``, the resolver will only see the installed version as a
candidate.

``--upgrade-strategy``

This option affects which packages are allowed to be installed. It is only
relevant if ``--upgrade`` is specified (except for the ``to-satisfy-only``
option mentioned below). The base behaviour is to allow
packages specified on pip's command line to be upgraded. This option controls
what *other* packages can be upgraded:

* ``eager`` - all packages will be upgraded to the latest possible version.
  It should be noted here that pip's current resolution algorithm isn't even
  aware of packages other than those specified on the command line, and
  those identified as dependencies. This may or may not be true of the new
  resolver.
* ``only-if-needed`` - packages are only upgraded if they are named in the
  pip command or a requirement file (i.e, they are direct requirements), or
  an upgraded parent needs a later version of the dependency than is
  currently installed.
* ``to-satisfy-only`` (**undocumented, please avoid**) - packages are not
  upgraded (not even direct requirements) unless the currently installed
  version fails to satisfy a requirement (either explicitly specified or a
  dependency).

  * This is actually the "default" upgrade strategy when ``--upgrade`` is
    *not set*, i.e. ``pip install AlreadyInstalled`` and
    ``pip install --upgrade --upgrade-strategy=to-satisfy-only AlreadyInstalled``
    yield the same behavior.

``--force-reinstall``

Doesn't affect resolution, but if the resolved result is the same as what is
currently installed, uninstall and reinstall it rather than leaving the
current version in place. This occurs even if ``--upgrade`` is not set.

``--ignore-installed``

Act as if the currently installed version isn't there - so don't care about
``--upgrade``, and don't uninstall before (re-)installing.


Controlling what gets considered
================================

These options affect the list of distribution files that the resolver will
consider as candidates for installation. As such, they affect the data that
the resolver has to work with, rather than influencing what pip does with the
resolution result.

Prereleases

``--pre``

Source vs Binary

``--no-binary``

``--only-binary``

``--prefer-binary``

Wheel tag specification

``--platform``

``--implementation``

``--abi``

Index options

``--index-url``

``--extra-index-url``

``--no-index``

``--find-links``


Controlling dependency data
===========================

These options control what dependency data the resolver sees for any given
package (or, in the case of ``--python-version``, the environment information
the resolver uses to *check* the dependency).

``--no-deps``

``--python-version``

``--ignore-requires-python``


Special cases
=============

These need further investigation. They affect the install process, but not
necessarily resolution or what gets installed.

``--require-hashes``

``--constraint``

``--editable <LOCATION>``


.. _still evolving: https://github.com/pypa/pip/issues/8115
