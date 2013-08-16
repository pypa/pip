Vendored libraries should not be modified except as required to actually
successfully vendor them.


Modifications
=============

* html5lib has been modified to import six from pip.vendor


Note to Downstream Distributors
===============================

Libraries are vendored/bundled inside of this directory in order to prevent
end users from needing to manually install packages if they accidently remove
something that pip depends on. Realizing that downstream prefers to unbundle
packages and that with the downstream package manager a user can use that to
fix their installation we've attempted to make it easier to unbundle the
included distributions.

All bundled packages exist in the ``pip.vendor`` namespace, and the versions
(fetched from PyPI) that we use are located in vendor.txt. After removing
``pip.vendor.*`` you'll also need to update the import statements that import
these packages.
