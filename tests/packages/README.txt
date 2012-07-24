This package exists for testing uninstall-rollback. 

Version 0.2broken has a setup.py crafted to fail on install (and only on
install). If any earlier step would fail (i.e. egg-info-generation), the
already-installed version would never be uninstalled, so uninstall-rollback
would not come into play.

The parent-0.1.tar.gz and child-0.1.tar.gz packages are used by
test_uninstall:test_uninstall_overlapping_package.
