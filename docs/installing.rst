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

Requirements
++++++++++++

.. note::

  setuptools-0.8 final is not released to pypi yet. Betas can be found here: https://bitbucket.org/pypa/setuptools/downloads

pip requires `setuptools`_. As of v1.4, pip recommends `setuptools`_ >=0.8, not
`distribute`_ (the fork of setuptools). `setuptools`_ and `distribute`_ are now
merged back together as "setuptools".

For details on installing setuptools from scratch, see the install instructions
on the `setuptools pypi page <https://pypi.python.org/pypi/setuptools>`_

If you already have `setuptools`_ or `distribute`_, then you can use pip to upgrade
it, but you'll need to upgrade pip first to v1.4 using one of the methods
below. Older versions of pip are *not* capable of performing the upgrade to the
latest setuptools.

You can upgrade to the latest setuptools in one of two ways, depending on what
you have currently. To determine what you have currently, run ``pip show
distribute``. If it returns results, then you have distribute.

If you currently have distribute, run ``pip install -U distribute``. This will
upgrade to you distribute-0.7, which is just a wrapper, that depends on
setuptools. The end result will be that you have distribute-0.7 (which does
nothing) *and* the latest setuptools installed. If you currently have
setuptools, just run ``pip install -U setuptools``.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute


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

