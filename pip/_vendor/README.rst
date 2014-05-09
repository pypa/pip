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


Markerlib and pkg_resources
===========================

Markerlib and pkg_resources has been pulled in from setuptools 3.4.4


Note to Downstream Distributors
===============================

Libraries are vendored/bundled inside of this directory in order to prevent
end users from needing to manually install packages if they accidently remove
something that pip depends on.

All bundled packages exist in the ``pip._vendor`` namespace, and the versions
(fetched from PyPI) that we use are located in vendor.txt. If you remove
``pip._vendor.*`` you'll also need to update the import statements that import
these packages.
