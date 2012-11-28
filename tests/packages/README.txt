
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
hash testing (altough this pkg isn't needed explicitly)

gmpy2-2.0.tar.gz
----------------
for testing finder logic when name *contains* the name of the package specified

HackedEggInfo
-------------
has it's own egg_info class

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

paxpkg.tar.bz2
--------------
tar with pax headers

pkgwithmpkg-1.0.tar.gz; pkgwithmpkg-1.0-py2.7-macosx10.7.mpkg.zip
-----------------------------------------------------------------
used for osx test case (tests.test_finder:test_no_mpkg)

simple-[123].0.tar.gz
---------------------
contains "simple" package; good for basic testing and version logic.

Upper-[12].0.tar.gz and requiresuppper-1.0.tar.gz
--------------------------------------------------
'requiresupper' requires 'upper'
used for testing case mismatch case for url requirements







