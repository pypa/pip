
.. _`pip download`:

pip download
------------

.. contents::

Usage
*****

.. pip-command-usage:: download

``pip download`` is used just like ``pip install --download`` was used in the past. The same rules apply to this command: it should be very comfortable to use.

Description
***********

.. pip-command-description:: download



Options
*******

.. pip-command-options:: download

.. pip-index-options::


Examples
********

1. Download a package and all of its dependencies

  ::

    $ pip download -d /tmp/wheelhouse SomePackage
    $ pip download --no-index --find-links=/tmp/wheelhouse -d /tmp/otherwheelhouse SomePackage


