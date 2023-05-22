
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


.. _`1-build-system-interface`:
.. rubric:: Build System Interface

This is now covered in :doc:`../reference/build-system/index`.

Differences to ``build``
------------------------

`build <https://pypi.org/project/build/>`_ is a simple tool which can among other things build
wheels for projects using PEP 517. It is comparable to the execution of ``pip wheel --no-deps .``.
It can also build source distributions which is not possible with ``pip``.
``pip wheel`` covers the wheel scope of ``build`` but offers many additional features.

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
