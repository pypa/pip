.. _`Installation`:

Installation
============

.. warning::

    Prior to version 1.3, pip did not use SSL for downloading packages from PyPI, and thus left
    users more vulnerable to security threats. We advise installing at least version 1.3.
    If you're using `virtualenv <http://www.virtualenv.org>`_ to install pip, we advise installing
    at least version 1.9, which contains pip version 1.3.


Python & OS Support
-------------------

pip v1.4 works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.



Using virtualenv
----------------

The easiest way to install and use pip is with `virtualenv
<http://www.virtualenv.org>`_, since every virtualenv has pip (and it's dependencies) installed into it
automatically.

This does not require root access or modify your system Python
installation. For instance::

    $ virtualenv my_env
    $ . my_env/bin/activate
    (my_env)$ pip install SomePackage

When used in this manner, pip will only affect the active virtual environment.

See the `virtualenv installation instructions <http://www.virtualenv.org/en/latest/#installation>`_.

Installing Globally
-------------------

pip can be installed globally in order to manage global packages.
Often this requires the installation to be performed as root.

.. warning::

    We advise against using `easy_install <http://pythonhosted.org/setuptools/easy_install.html>`_ to install pip, because easy_install
    does not download from PyPI over SSL, so the installation might be insecure.

.. _`Installation Requirements`:

Requirements
++++++++++++

pip requires `setuptools`_.

.. warning::

    As of pip 1.4, pip recommends `setuptools`_ >=0.8, not `distribute`_ (a
    fork of setuptools) and the wheel support *requires* `setuptools`_ >=0.8.
    `setuptools`_ and `distribute`_ are now merged back together as
    "setuptools".

For details on installing setuptools from scratch, see the install instructions
on the `setuptools pypi page <https://pypi.python.org/pypi/setuptools>`_

If you already have `setuptools`_ or `distribute`_ (and pip), you can upgrade
like so::

    pip install --upgrade setuptools

If you had distribute before, this will upgrade to you distribute-0.7.X, which
is just a wrapper, that depends on setuptools. The end result will be that you
have distribute-0.7.X (which does nothing) *and* the latest setuptools
installed.


.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute


.. _`get-pip`:

Using get-pip
+++++++++++++

::

 $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
 $ [sudo] python get-pip.py


Installing from source
++++++++++++++++++++++

::

 $ curl -O https://pypi.python.org/packages/source/p/pip/pip-X.X.tar.gz
 $ tar xvfz pip-X.X.tar.gz
 $ cd pip-X.X
 $ [sudo] python setup.py install

