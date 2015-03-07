
.. _`pip wheel`:

pip wheel
---------

.. contents::

Usage
*****

.. pip-command-usage:: wheel


Description
***********

.. pip-command-description:: wheel


Build System Interface
++++++++++++++++++++++

In order for pip to build a wheel, ``setup.py`` must implement the
``bdist_wheel`` command with the following syntax::

    python setup.py bdist_wheel -d TARGET

This command must create a wheel compatible with the invoking Python
interpreter, and save that wheel in the directory TARGET.

No other build system commands are invoked by the ``pip wheel`` command.

Customising the build
~~~~~~~~~~~~~~~~~~~~~

It is possible using ``--global-option`` to include additional build commands
with their arguments in the ``setup.py`` command. This is currently the only
way to influence the building of C extensions from the command line. For
example::

    pip wheel --global-option bdist_ext --global-option -DFOO wheel

will result in a build command of

::

    setup.py bdist_ext -DFOO bdist_wheel -d TARGET

which passes a preprocessor symbol to the extension build.

Such usage is considered highly build-system specific and more an accident of
the current implementation than a supported interface.



Options
*******

.. pip-command-options:: wheel

.. pip-index-options::


Examples
********

1. Build wheels for a requirement (and all its dependencies), and then install

  ::

    $ pip wheel --wheel-dir=/tmp/wheelhouse SomePackage
    $ pip install --no-index --find-links=/tmp/wheelhouse SomePackage


