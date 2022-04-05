.. _`pip hash`:

========
pip hash
========


Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: hash "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: hash "py -m pip"


Description
===========

.. pip-command-description:: hash

Overview
--------

``pip hash`` is a convenient way to get a hash digest for use with
:ref:`hash-checking mode`, especially for packages with multiple archives. The
error message from ``pip install --require-hashes ...`` will give you one
hash, but, if there are multiple archives (like source and binary ones), you
will need to manually download and compute a hash for the others. Otherwise, a
spurious hash mismatch could occur when :ref:`pip install` is passed a
different set of options, like :ref:`--no-binary <install_--no-binary>`.


Options
=======

.. pip-command-options:: hash


Example
=======

Compute the hash of a downloaded archive:

.. tab:: Unix/macOS

   .. code-block:: console

      $ python -m pip download SomePackage
      Collecting SomePackage
         Downloading SomePackage-2.2.tar.gz
         Saved ./pip_downloads/SomePackage-2.2.tar.gz
      Successfully downloaded SomePackage
      $ python -m pip hash ./pip_downloads/SomePackage-2.2.tar.gz
      ./pip_downloads/SomePackage-2.2.tar.gz:
      --hash=sha256:93e62e05c7ad3da1a233def6731e8285156701e3419a5fe279017c429ec67ce0

.. tab:: Windows

   .. code-block:: console

      C:\> py -m pip download SomePackage
      Collecting SomePackage
         Downloading SomePackage-2.2.tar.gz
         Saved ./pip_downloads/SomePackage-2.2.tar.gz
      Successfully downloaded SomePackage
      C:\> py -m pip hash ./pip_downloads/SomePackage-2.2.tar.gz
      ./pip_downloads/SomePackage-2.2.tar.gz:
      --hash=sha256:93e62e05c7ad3da1a233def6731e8285156701e3419a5fe279017c429ec67ce0
