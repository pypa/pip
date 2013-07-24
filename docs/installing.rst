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

If you already have virtualenv installed, then the easiest way to use pip is through `virtualenv
<http://www.virtualenv.org>`_, since every virtualenv has pip (and its dependencies) installed into it
automatically.

This does not require root access or modify your system Python
installation. For instance::

    $ virtualenv my_env
    $ . my_env/bin/activate
    (my_env)$ pip install SomePackage

When used in this manner, pip will only affect the active virtual environment.

To ensure the virtual environment includes the latest version of pip, run::

    $ pip install --upgrade pip

Since the only beginner (and Windows) friendly
`virtualenv installation instructions <http://www.virtualenv.org/en/latest/#installation>`_
suggest using pip to install it, if the first command above doesn't work try the next section.


Bootstrapping pip and virtualenv
--------------------------------

Linux
~~~~~

On Linux, pip and virtualenv will generally be available through the system package manager.
Recent versions of common desktop Linux distributions include suitably recent versions of
both, so for global installation into the system Python, it is recommended to use the
system package manager versions, and then use virtualenv as described above.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip python-virtualenv

On Fedora::

   $ sudo yum install python-pip python-virtualenv

While these may not always be the most up to date versions of ``pip``, the instructions
above will ensure that the latest version is installed into virtual environments without
risking any adverse effects on the system installation of Python.


Other operating systems (including Windows and Mac OS X)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On other operating systems, the following commands should install pip for the current user::

   $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
   $ python get-pip.py --user

If you don't have ``curl`` installed (for example, on Windows) you can download ``get-pip.py``
from the given URL and run it as shown in the second command.

Once you have pip installed, you can use it to retrieve virtualenv::

   $ pip install --user virtualenv

And then proceed to use virtualenv as shown above.


Installing pip for all users
----------------------------

pip can be installed globally in order to manage global packages.
As this typically requires the installation to be performed with administrator
privileges, and (on Linux systems) may conflict with packages provided through
the system package manager, it is *not* the recommended approach.

The simplest way to perform a global installation is to use the bootstrapping
instruction above, but running the get-pip.py script with additional privileges.
However, since running a script you downloaded from the internet with that level
of access to your system should worry you, here are some more detailed instructions
on the steps involved.

Note: the instructions below won't work on Windows. Windows users are strongly encouraged
to use the per user bootstrapping described above.

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

If you had distribute before, this will upgrade you to distribute-0.7.X, which
is just a wrapper, that depends on setuptools. The end result will be that you
have distribute-0.7.X (which does nothing) *and* the latest setuptools
installed.


.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute

Once a suitable version of setuptools is available, pip can be installed
from source::

 $ curl -O https://pypi.python.org/packages/source/p/pip/pip-X.X.tar.gz
 $ tar xvfz pip-X.X.tar.gz
 $ cd pip-X.X
 $ sudo python setup.py install

Since even these more explicit instructions still involve running an arbitrary
script from the internet with elevated privileges, the user level bootstrapping
described above is *strongly* recommended.
