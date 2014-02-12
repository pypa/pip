
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
