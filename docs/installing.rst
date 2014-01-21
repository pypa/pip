.. _`Installation`:

Installation
============

Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3, 3.4 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.


.. _`get-pip`:

Install or Upgrade pip
----------------------

To install or upgrade pip, securely download `get-pip.py
<https://raw.github.com/pypa/pip/master/contrib/get-pip.py>`_. [1]_

Then run the following (which may require administrator access)::

 $ python get-pip.py

.. note::

    Beginning with v1.5.1, pip does not require `setuptools`_ prior to running
    `get-pip.py`. Additionally, if `setuptools`_ (or `distribute`_) is not
    already installed, `get-pip.py` will install `setuptools`_ for you.


Using Package Managers
----------------------

On Linux, pip will generally be available for the system install of python using
the system package manager, although often the latest version will be
unavailable.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip

On Fedora::

   $ sudo yum install python-pip


.. [1] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute


