This package exists for testing uninstall-rollback. 

Version 0.2broken has a setup.py crafted to fail on install (and only on
install). If any earlier step would fail (i.e. egg-info-generation), the
already-installed version would never be uninstalled, so uninstall-rollback
would not come into play.
