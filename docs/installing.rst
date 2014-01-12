.. _`Installation`:

Installation
============

Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.


.. _`get-pip`:

Install or Upgrade pip
----------------------

Beginning with pip v1.5.1, pip can execute all of it's commands, and install
from :ref:`wheels <Building and Installing Wheels>`, without having
`setuptools`_ installed. `setuptools`_ is required when installing from Source
Distributions (i.e the `*.tar.gz` or `*.zip` files from PyPI).

To install pip, securely download `get-pip.py <https://raw.github.com/pypa/pip/master/contrib/get-pip.py>`_. [2]_

Then run the following (which may require administrator access), to install (or upgrade to) the
latest version of pip::

 $ python get-pip.py


Install or Upgrade Setuptools
-----------------------------

pip requires `setuptools`_ when installing Source Distributions, not when installing from wheels.

To install setuptools

::

$ pip install setuptools


To upgrade setuptools:

::

$ pip install --upgrade setuptools

   .. note::

      If you have distribute, this will upgrade to you distribute-0.7.X, which
      is just a wrapper, that depends on setuptools. The end result will be that
      you have distribute-0.7.X (which does nothing) *and* the latest setuptools
      installed.  If you'd prefer not to end up with the distribute wrapper,
      then instead, run ``$ pip uninstall distribute``, then ``$ pip install
      setuptools``.


Using Package Managers
----------------------

On Linux, pip will generally be available for the system install of python using the system package manager,
although often the latest version lags behind. Installing `python-pip` will also install `python-setuptools`.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip

On Fedora::

   $ sudo yum install python-pip


.. [1] As of pip 1.4, pip started requiring `setuptools`_, not `distribute`_
       (a fork of setuptools). `setuptools`_ and `distribute`_ are now merged
       back together as "setuptools".
.. [2] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute


