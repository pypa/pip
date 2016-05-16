
.. _`pip download`:

pip download
------------

.. contents::

Usage
*****

.. pip-command-usage:: download


Description
***********

.. pip-command-description:: download


Overview
++++++++
``pip download`` replaces the ``--download`` option to ``pip install``,
which is now deprecated and will be removed in pip 10.

``pip download`` does the same resolution and downloading as ``pip install``,
but instead of installing the dependencies, it collects the downloaded
distributions into the directory provided (defaulting to the current
directory). This directory can later be passed as the value to
``pip install --find-links`` to facilitate offline or locked down package
installation.


Options
*******

.. pip-command-options:: download

.. pip-index-options::


Examples
********

#. Download a package and all of its dependencies

    ::

      $ pip download SomePackage
      $ pip download -d . SomePackage  # equivalent to above
      $ pip download --no-index --find-links=/tmp/wheelhouse -d /tmp/otherwheelhouse SomePackage
