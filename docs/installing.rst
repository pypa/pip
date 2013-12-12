.. _`Installation`:

Installation
============

Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.


Install or Upgrade Setuptools
-----------------------------

pip requires `setuptools`_ and it has to be installed first, before pip can run. [1]_

To install setuptools from scratch:

1. Securely download `ez_setup.py <https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py>`_. [2]_

2. Then run the following (which may require administrator access)::

   $ python ez_setup.py


   .. warning::

      Prior to Setuptools-1.0, `ez_setup.py` was not secure, and is currently
      only secure when your environment contains secure versions of either
      `curl`, `wget`, or `powershell`. [2]_  If you're not sure if you're
      environment fulfills this requirement, then the safest approach is to
      securely download the setuptools archive directly from `PyPI
      <https://pypi.python.org/pypi/setuptools/>`_, unpack it, and run "python
      setup.py install" from inside the unpacked directory.


To upgrade a previous install of `setuptools`_ or `distribute`_, there are two scenarios.


1. You currently have setuptools or distribute *and* some version of pip::

   $ pip install --upgrade setuptools

   If you have distribute, this will upgrade to you distribute-0.7.X, which is
   just a wrapper, that depends on setuptools. The end result will be that you
   have distribute-0.7.X (which does nothing) *and* the latest setuptools
   installed.

2. You currently have setuptools or distribute, but not pip:

   Follow the pip install procedure below, then come back and run::

   $ pip install --upgrade setuptools


.. _`get-pip`:

Install or Upgrade pip
----------------------

Securely download `get-pip.py <https://raw.github.com/pypa/pip/master/contrib/get-pip.py>`_. [2]_

Then run the following (which may require administrator access), to install (or upgrade to) the
latest version of pip::

 $ python get-pip.py


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


