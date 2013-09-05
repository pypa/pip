Quickstart
==========

Install a package:

::

  $ pip install SomePackage==1.0
    [...]
    Successfully installed SomePackage

Show what files were installed:

::

  $ pip show --files SomePackage
    Name: SomePackage
    Version: 1.0
    Location: /my/env/lib/pythonx.x/site-packages
    Files:
     ../somepackage/__init__.py
     [...]

List what packages are outdated:

::

  $ pip list --outdated
    SomePackage (Current: 1.0 Latest: 2.0)

Upgrade a package:

::

  $ pip install --upgrade SomePackage
    [...]
    Found existing installation: SomePackage 1.0
    Uninstalling SomePackage:
      Successfully uninstalled SomePackage
    Running setup.py install for SomePackage
    Successfully installed SomePackage

Uninstall a package:

::

  $ pip uninstall SomePackage
    Uninstalling SomePackage:
      /my/env/lib/pythonx.x/site-packages/somepackage
    Proceed (y/n)? y
    Successfully uninstalled SomePackage

