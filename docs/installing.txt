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

pip works with CPython versions 2.5, 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.


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

    We advise against using `easy_install <http://pythonhosted.org/distribute/easy_install.html>`_ to install pip, because easy_install
    does not download from PyPI over SSL, so the installation might be insecure.
    Since pip can then be used to install packages (which execute code on
    your computer), it is better to go through a trusted path.


Requirements
++++++++++++

pip requires either `setuptools <https://pypi.python.org/pypi/setuptools>`_
or `distribute <https://pypi.python.org/pypi/distribute>`_.

See the `Distribute Install Instructions <https://pypi.python.org/pypi/distribute/>`_ or the
`Setuptools Install Instructions <https://pypi.python.org/pypi/setuptools#installation-instructions>`_

If installing pip using a linux package manager, these requirements will be installed for you.

.. warning::

    If you are using Python 3.X you **must** use distribute; setuptools doesn't
    support Python 3.X.


Using get-pip
+++++++++++++

After installing the requirements:

::

 $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
 $ [sudo] python get-pip.py


Installing from source
++++++++++++++++++++++

After installing the requirements:

::

 $ curl -O https://pypi.python.org/packages/source/p/pip/pip-X.X.tar.gz
 $ tar xvfz pip-X.X.tar.gz
 $ cd pip-X.X
 $ [sudo] python setup.py install

