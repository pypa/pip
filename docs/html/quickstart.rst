==========
Quickstart
==========

pip is a command line tool for installing Python packages.

For a full tutorial on installing packages with pip, see the
`Python Packaging User Guide`_

For a more detailed exploration of pip's functionality see the pip
:doc:`User Guide <user_guide>`.

Quick Setup
===========

1. Check pip installation
-------------------------
Check if you already have pip installed by running:

.. code-block:: console

  pip --version

See :doc:`installing pip <installing>`for more information, or to troubleshoot
any problems.

2. Check pip is up to date
--------------------------

To make sure you are running pip's latest version, run:

.. tab:: Unix/macOS

   .. code-block:: console

      python -m pip install -U pip

.. tab:: Windows

   .. code-block:: console

      py -m pip install -U pip


3. Set up a virtual environment
-------------------------------

Before using pip, we recommend you set up and use a virtual environment to
isolate your project packages.

See `Creating Virtual Environments`_ for more information.

Common tasks
============

Install a package from `PyPI`_
------------------------------

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip install SomePackage
      [...]
      Successfully installed SomePackage

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip install SomePackage
      [...]
      Successfully installed SomePackage

Install a package from GitHub
------------------------------

Pip can install packages from common version control systems (VCS), including
GitHub.

For example, to install a specific commit from the Django project, run:

.. code-block:: console

  pip install git+https://github.com/django/django.git@45dfb3641aa4d9828a7c5448d11aa67c7cbd7966

See VCS support for more information.

Install a package you have already downloaded
---------------------------------------------

This is useful if the target machine does not have a network connection:

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip install SomePackage-1.0-py2.py3-none-any.whl
      [...]
      Successfully installed SomePackage

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip install SomePackage-1.0-py2.py3-none-any.whl
      [...]
      Successfully installed SomePackage

Install packages from a file
----------------------------

Many Python projects use a requirements.txt file to specify the list of packages
that need to be installed for the project to run. To install the packages
listed in the file, run:

.. code-block:: console

  pip install -r requirements.txt


Upgrade a package
-----------------

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip install --upgrade SomePackage
      [...]
      Found existing installation: SomePackage 1.0
      Uninstalling SomePackage:
      Successfully uninstalled SomePackage
      Running setup.py install for SomePackage
      Successfully installed SomePackage

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip install --upgrade SomePackage
      [...]
      Found existing installation: SomePackage 1.0
      Uninstalling SomePackage:
      Successfully uninstalled SomePackage
      Running setup.py install for SomePackage
      Successfully installed SomePackage

Uninstall a package
-------------------

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip uninstall SomePackage
      Uninstalling SomePackage:
      /my/env/lib/pythonx.x/site-packages/somepackage
      Proceed (y/n)? y
      Successfully uninstalled SomePackage

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip uninstall SomePackage
      Uninstalling SomePackage:
         /my/env/lib/pythonx.x/site-packages/somepackage
      Proceed (y/n)? y
      Successfully uninstalled SomePackage


For a full list of pip commands, see the pip reference guide.

.. _PyPI: https://pypi.org/
.. _Python Packaging User Guide: https://packaging.python.org/tutorials/installing-packages
.. _Creating Virtual Environments: https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments
