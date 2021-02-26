
.. _`pip wheel`:

=========
pip wheel
=========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: wheel "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: wheel "py -m pip"


Description
===========

.. pip-command-description:: wheel


Build System Interface
----------------------

In order for pip to build a wheel, ``setup.py`` must implement the
``bdist_wheel`` command with the following syntax:

.. tab:: Unix/macOS

   .. code-block:: shell

      python setup.py bdist_wheel -d TARGET

.. tab:: Windows

   .. code-block:: shell

      py setup.py bdist_wheel -d TARGET


This command must create a wheel compatible with the invoking Python
interpreter, and save that wheel in the directory TARGET.

No other build system commands are invoked by the ``pip wheel`` command.

Customising the build
^^^^^^^^^^^^^^^^^^^^^

It is possible using ``--global-option`` to include additional build commands
with their arguments in the ``setup.py`` command. This is currently the only
way to influence the building of C extensions from the command line. For
example:

.. tab:: Unix/macOS

   .. code-block:: shell

      python -m pip wheel --global-option bdist_ext --global-option -DFOO wheel

.. tab:: Windows

   .. code-block:: shell

      py -m pip wheel --global-option bdist_ext --global-option -DFOO wheel


will result in a build command of

::

    setup.py bdist_ext -DFOO bdist_wheel -d TARGET

which passes a preprocessor symbol to the extension build.

Such usage is considered highly build-system specific and more an accident of
the current implementation than a supported interface.



Options
=======

.. pip-command-options:: wheel

.. pip-index-options:: wheel


Examples
========

#. Build wheels for a requirement (and all its dependencies), and then install

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip wheel --wheel-dir=/tmp/wheelhouse SomePackage
         python -m pip install --no-index --find-links=/tmp/wheelhouse SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip wheel --wheel-dir=/tmp/wheelhouse SomePackage
         py -m pip install --no-index --find-links=/tmp/wheelhouse SomePackage

#. Build a wheel for a package from source

   .. tab:: Unix/macOS

      .. code-block:: shell

         python -m pip wheel --no-binary SomePackage SomePackage

   .. tab:: Windows

      .. code-block:: shell

         py -m pip wheel --no-binary SomePackage SomePackage
