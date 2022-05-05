
Details on Test Packages
========================

broken-0.1.tar.gz
-----------------
This package exists for testing uninstall-rollback.

broken-0.2broken.tar.gz
-----------------------
Version 0.2broken has a setup.py crafted to fail on install (and only on
install). If any earlier step would fail (i.e. egg-info-generation), the
already-installed version would never be uninstalled, so uninstall-rollback
would not come into play.

brokenegginfo-0.1.tar.gz
------------------------
crafted to fail on egg_info

BrokenEmitsUTF8
---------------
for generating unicode error in py3.x

duplicate-1.0.tar.gz
--------------------
for testing finding dupes across multiple find-links

FSPkg
-----
for installing from the file system

gmpy-1.15.tar.gz
----------------
hash testing (although this pkg isn't needed explicitly)

gmpy2-2.0.tar.gz
----------------
for testing finder logic when name *contains* the name of the package specified

HackedEggInfo
-------------
has its own egg_info class

LineEndings
-----------
contains DOS line endings

LocalExtras
-----------
has an extra in a local file:// dependency link

parent/child-0.1.tar.gz
-----------------------
The parent-0.1.tar.gz and child-0.1.tar.gz packages are used by
test_uninstall:test_uninstall_overlapping_package.

pkgwithmpkg-1.0.tar.gz; pkgwithmpkg-1.0-py2.7-macosx10.7.mpkg.zip
-----------------------------------------------------------------
used for osx test case (tests.test_finder:test_no_mpkg)

priority-*
----------
used for testing wheel priority over sdists

TopoRequires[1234][-0.0.1.tar.gz]
--------------------------------

These are used for testing topological handling of requirements: we have
TopoRequires, which is install-required by TopoRequires2 and TopoRequires3
and finally TopoRequires4 which install-requires both TopoRequires2 and 3
and also install-Requires TopoRequires.
This creates a diamond where no matter which way we walk without topological
awareness we'll end up attempting to install TopoRequires after one of
TopoRequires2, TopoRequires3 or TopoRequires4. (prefix iteration works as its
topological, suffix iteration likewise, infix breaks).

simple[2]-[123].0.tar.gz
------------------------
contains "simple[2]" package; good for basic testing and version logic.

wheelbroken-0.1.tar.gz
----------------------
fails for "setup.py bdist_wheel"

Upper-[12].0.tar.gz and requiresuppper-1.0.tar.gz
--------------------------------------------------
'requiresupper' requires 'upper'
used for testing case mismatch case for url requirements

meta-1.0-py2.py3-none-any.whl
--------------------------------------------------
Is an empty package which install_requires the simple and simple2 packages.

requires_simple_extra-0.1-py2.py3-none-any.whl
----------------------------------------------
requires_simple_extra[extra] requires simple==1.0

requires_wheelbroken_upper
--------------------------
Requires wheelbroken and upper - used for testing implicit wheel building
during install.

require_simple-1.0.tar.gz
------------------------
contains "require_simple" package which requires simple>=2.0 - used for testing
if dependencies are handled correctly.
