.. _`Installation`:

Installation
============


Python & OS Support
-------------------

pip works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.


.. _`Recommended Procedure`:

Virtualenv Procedure (recommended)
----------------------------------

We recommend getting `virtualenv`_ first, and then using that to create virtual
environments that contain `pip`_ (and `setuptools`_) for the following reasons:

#. It doesn't require administrator access.
#. It doesn't modify your system Python which can possibly result in system failures.
#. It's simple and gives you the flexibility to work from any python installed
   on your system.
#. You'll end up with versions of pip, virtualenv, and setuptools that have been
   tested together.


Get virtualenv
++++++++++++++

Download the latest virtualenv from here: https://pypi.python.org/pypi/virtualenv/

The file you'll be downloading will be of the form "virtualenv-X.Y.tar.gz"

.. warning::

    You must use virtualenv>=1.9.1 (which contains pip>=1.3.1) to ensure pip
    verifies certificates over SSL when installing.

Unpack the downloaded file and place the contents into your home directory (or
user directory on Windows), or other directory of your choice.

We will not be *installing* virtualenv.


Create an environment
+++++++++++++++++++++

Assuming the following:

* On linux/OSX, your python interpreter of choice is available as "pythonX.Y"
* On Windows, your python interpreter of choice is available as "c:\\PythonXY\\python"
* In your console, you are in the directory you unpacked the download file into.

Then use virtualenv, like so, to create a virtual environment (that contains pip
and setuptools).

E.g, in this case, we'll be creating an environment labeled
`myVE`, short for "my virtual environment".

On linux/OSX::

   $ pythonX.Y virtualenv-X.Y/virtualenv.py myVE

On Windows::

   $ c:\pythonXY\python virtualenv-X.Y/virtualenv.py myVE


Use the environment
+++++++++++++++++++

To use the `myVE` environment, activate it like so.

On linux/OSX::

   $ source myVE/bin/active

On Windows::

   $ myVE\Scripts\activate.bat


As a result, ``pip`` will be on your path, and will install packages to the `myVE` environment.

.. _`Advanced Procedure`:

Global Procedures
-----------------

Although we recommend the vitualenv procedure above, there are cases where a
user might want to install pip and setuptools globally for a python install on
their system.  There are two options here:

1. Using the bootstap scripts for setuptools and pip
2. On linux, for the system python, using the system package manager.

Note that these methods will usually require administrator access.


Using the bootstrap scripts
+++++++++++++++++++++++++++

Install/Upgrade Setuptools
~~~~~~~~~~~~~~~~~~~~~~~~~~

pip requires `setuptools`_.

.. warning::

    As of pip 1.4, pip recommends `setuptools`_ >=0.8, not `distribute`_ (a
    fork of setuptools) and the wheel support *requires* `setuptools`_ >=0.8.
    `setuptools`_ and `distribute`_ are now merged back together as
    "setuptools".

To install setuptools from scratch, download `ez_setup.py` from here:
https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py.

Then run it like so::

   $ python ez_setup.py


To upgrade a previous install of setuptools or distribute, there are two scenarios.


1. You currently have setuptools or distribute *and* some version of pip::

   $ pip install --upgrade setuptools

   If you have distribute, this will upgrade to you distribute-0.7.X, which is
   just a wrapper, that depends on setuptools. The end result will be that you
   have distribute-0.7.X (which does nothing) *and* the latest setuptools
   installed.

2. You currently have setuptools or distribute, but not pip:

   Follow the pip install procedure below, then come back and run::

   $ pip install --upgrade setuptools



Install/Upgrade pip
~~~~~~~~~~~~~~~~~~~

Download `get-pip.py` from here: https://raw.github.com/pypa/pip/master/contrib/get-pip.py

Then run the following (which may require administrator access), to install or upgrade to the
latest pip::

 $ python get-pip.py


Using Package Managers
++++++++++++++++++++++

On Linux, pip will generally be available for the system install of python using the system package manager,
although often the latest version lags behind. Installing `python-pip` will also install `python-setuptools`.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip

On Fedora::

   $ sudo yum install python-pip


.. _pip: http://www.pip-installer.org
.. _virtualenv: http://www.virtualenv.org
.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute
