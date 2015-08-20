Policy
======

Vendored libraries should not be modified except as required to actually
successfully vendor them.


Modifications
=============

* html5lib has been modified to import six from pip._vendor
* pkg_resources has been modified to import _markerlib from pip._vendor
* markerlib has been modified to import its API from pip._vendor
* CacheControl has been modified to import it's dependencies from pip._vendor
* progress has been modified to not use unicode literals for support for Python 3.2


_markerlib and pkg_resources
============================

_markerlib and pkg_resources has been pulled in from setuptools 18.2


Note to Downstream Distributors
===============================

Libraries are vendored/bundled inside of this directory in order to prevent
end users from needing to manually install packages if they accidently remove
something that pip depends on.

All bundled packages exist in the ``pip._vendor`` namespace, and the versions
(fetched from PyPI) that we use are located in ``vendor.txt``. If you wish
to debundle these you can do so by either deleting everything in
``pip/_vendor`` **except** for ``pip/_vendor/__init__.py`` or by running
``PIP_NO_VENDOR_FOR_DOWNSTREAM=1 setup.py install``. No other changes should
be required as the ``pip/_vendor/__init__.py`` file will alias the "real"
names (such as ``import six``) to the bundled names (such as
``import pip._vendor.six``) automatically. Alternatively if you delete the
entire ``pip._vendor`` you will need to adjust imports that import from those
locations.
