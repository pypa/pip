============
Cookbook
============

.. _`Requirements Files`:

Requirements Files
******************

"Requirements files" are files containing a list of items to be
installed using :ref:`pip install -r <install_--requirement>` like so:

 ::

   pip install -r requirements.txt


Details on the format of the files are here: :ref:`Requirements File Format`.


There are 3 common use cases for requirements files:

1. When installing many things, it's easier to use a requirements file,
   than specifying them all on the command line.

2. Requirements files are often used to hold the result from :ref:`pip freeze`
   for the purpose of achieving :ref:`repeatable installations <Repeatability>`.
   In this case, your requirement file contains a pinned version of everything
   that was installed when `pip freeze` was run.

   ::

     pip freeze > requirements.txt
     pip install -r requirements.txt

3. Requirements files can be used to force pip to properly resolve dependencies.
   As it is now, pip `doesn't have true dependency resolution
   <https://github.com/pypa/pip/issues/988>`_, but instead simply uses the first
   specification it finds for a project. E.g if `pkg1` requires `pkg3>=1.0` and
   `pkg2` requires `pkg3>=1.0,<=2.0`, and if `pkg1` is resolved first, pip will
   only use `pkg3>=1.0`, and could easily end up installing a version of `pkg3`
   that conflicts with the needs of `pkg2`.  To solve this problem, you can
   place `pkg3>=1.0,<=2.0` (i.e. the correct specification) into your
   requirements file directly along with the other top level requirements. Like
   so:

   ::

     pkg1
     pkg2
     pkg3>=1.0,<=2.0


It's important to be clear that pip determines package dependencies using `install_requires metadata
<http://pythonhosted.org/setuptools/setuptools.html#declaring-dependencies>`_, not by discovering `requirements.txt`
files embedded in projects.

For a good discussion on the conceptual differences between setup.py and
requirements, see `"setup.py vs requirements.txt" (an article by Donald Stufft)
<https://caremad.io/blog/setup-vs-requirement/>`_

See also:

* :ref:`Requirements File Format`
* :ref:`pip freeze`


.. _`Fast & Local Installs`:

Fast & Local Installs
*********************

Often, you will want a fast install from local archives, without probing PyPI.

First, :ref:`download the archives <Downloading Archives>` that fulfill your requirements::

$ pip install --download <DIR> -r requirements.txt

Then, install using  :ref:`--find-links <--find-links>` and :ref:`--no-index <--no-index>`::

$ pip install --no-index --find-links=[file://]<DIR> -r requirements.txt


.. _`Building and Installing Wheels`:

Building and Installing Wheels
******************************

"Wheel" is a built, archive format that can greatly speed installation compared
to building and installing from source archives. For more information, see the
`Wheel docs <http://wheel.readthedocs.org>`_ ,
`PEP427 <http://www.python.org/dev/peps/pep-0427>`_, and
`PEP425 <http://www.python.org/dev/peps/pep-0425>`_

Pip prefers Wheels where they are available, to disable this use the
:ref:`--no-use-wheel <install_--no-use-wheel>` flag for :ref:`pip install`.

If no satisfactory wheels are found, pip will default to finding source archives.

.. note::

  pip currently disallows platform-specific wheels (except for Windows and Mac)
  from being downloaded from PyPI.  See :ref:`Should you upload wheels to PyPI`.


To install directly from a wheel archive:

::

 pip install SomePackage-1.0-py2.py3-none-any.whl


pip additionally offers :ref:`pip wheel` as a convenience, to build wheels for
your requirements and dependencies.

:ref:`pip wheel` requires the `wheel package <https://pypi.python.org/pypi/wheel>`_ to be installed,
which provides the "bdist_wheel" setuptools extension that it uses.

To build wheels for your requirements and all their dependencies to a local directory:

::

 pip install wheel
 pip wheel --wheel-dir=/local/wheels -r requirements.txt


.. warning::

  Currently, when ``pip wheel`` finds a wheel for one of your requirements
  already on PyPI, it does not rebuild, and it does not place the file in your
  wheelhouse dir.  There is an issue open to change this
  (https://github.com/pypa/pip/issues/1310)



And *then* to install those requirements just using your local directory of wheels (and not from PyPI):

::

 pip install --no-index --find-links=/local/wheels -r requirements.txt


.. _`Should you upload wheels to PyPI`:

Should you upload wheels to PyPI?
---------------------------------

The wheel format can eliminate a lot of redundant compilation but, alas,
it's not generally advisable to upload your pre-compiled linux-x86-64
library binding to pypi. Wheel's tags are only designed to express
the most important *Python*-specific compatibility concerns (Python
version, ABI, and architecture) but do not represent other important
binary compatibility factors such as the OS release, patch level, and
the versions of all the shared library dependencies of any extensions
inside the package.

Rather than representing all possible compatibility information in the
wheel itself, the wheel design suggests distribution-specific build
services (e.g. a separate index for Fedora Linux binary wheels, compiled
by the index maintainer). This is the same solution taken by Linux
distributions which all re-compile their own packages instead of installing
each other's binary packages.

Some kinds of precompiled C extension modules can make sense on PyPI, even
for Linux. Good examples include things that can be sensibly statically
linked (a cryptographic hash function; an accelerator module that is
not a binding for an external library); the best example of something
that shouldn't be statically linked is a library like openssl that needs
to be constantly kept up-to-date for security. Regardless of whether a
compatible pre-build package is available, many Linux users will prefer
to always compile their own anyway.

On Windows and Mac, the case for binary wheels on pypi is stronger due to the
systems being much more uniform than Linux and because it's harder for the end
user to compile their own. Windows and Mac wheels uploaded to pypi should be
compatible with the Python distributions downloaded from http://python.org/.  If
you already upload other binary formats to pypi, upload wheels as well.  Unlike
the older formats, wheels are compatible with virtual environments.


.. _`Downloading Archives`:

Downloading archives
********************

pip allows you to *just* download the source archives for your requirements, without installing anything and without regard to what's already installed.

::

$ pip install --download <DIR> -r requirements.txt

or, for a specific package::

$ pip install --download <DIR> SomePackage


Unpacking archives
******************

pip allows you to *just* unpack archives to a build directory without installing them to site-packages.  This can be useful to troubleshoot install errors or to inspect what is being installed.

::

$ pip install --no-install SomePackage

If you're in a virtualenv, the build dir is ``<virtualenv path>/build``.  Otherwise, it's ``<OS temp dir>/pip-build-<username>``

Afterwards, to finish the job of installing unpacked archives, run::

$ pip install --no-download SomePackage



Non-recursive upgrades
************************

``pip install --upgrade`` is currently written to perform a recursive upgrade.

E.g. supposing:

* `SomePackage-1.0` requires `AnotherPackage>=1.0`
* `SomePackage-2.0` requires `AnotherPackage>=1.0` and `OneMorePoject==1.0`
* `SomePackage-1.0` and `AnotherPackage-1.0` are currently installed
* `SomePackage-2.0` and `AnotherPackage-2.0` are the latest versions available on PyPI.

Running ``pip install --upgrade SomePackage`` would upgrade `SomePackage` *and* `AnotherPackage`
despite `AnotherPackage` already being satisifed.

If you would like to perform a non-recursive upgrade perform these 2 steps::

  pip install --upgrade --no-deps SomePackage
  pip install SomePackage

The first line will upgrade `SomePackage`, but not dependencies like `AnotherPackage`.  The 2nd line will fill in new dependencies like `OneMorePackage`.


.. _`Repeatability`:

Ensuring Repeatability
**********************

Three things are required to fully guarantee a repeatable installation using requirements files.

1. The requirements file was generated by ``pip freeze`` or you're sure it only
   contains requirements that specify a specific version.
2. The installation is performed using :ref:`--no-deps <install_--no-deps>`.
   This guarantees that only what is explicitly listed in the requirements file is
   installed.
3. The installation is performed against an index or find-links location that is
   guaranteed to *not* allow archives to be changed and updated without a
   version increase.  Unfortunately, this is *not* true on PyPI. It is possible
   for the same pypi distribution to have a different hash over time. Project
   authors are allowed to delete a distribution, and then upload a new one with
   the same name and version, but a different hash. See `Issue #1175
   <https://github.com/pypa/pip/issues/1175>`_ for plans to add hash
   confirmation to pip, or a new "lock file" notion, but for now, know that the `peep
   project <https://pypi.python.org/pypi/peep>`_ offers this feature on top of pip
   using requirements file comments.

User Installs
*************

With Python 2.6 came the `"user scheme" for installation
<http://docs.python.org/install/index.html#alternate-installation-the-user-scheme>`_, which means that all
Python distributions support an alternative install location that is specific to a user.
The default location for each OS is explained in the python documentation
for the `site.USER_BASE <http://docs.python.org/library/site.html#site.USER_BASE>`_ variable.
This mode of installation can be turned on by
specifying the :ref:`--user <install_--user>` option to ``pip install``.

Moreover, the "user scheme" can be customized by setting the
``PYTHONUSERBASE`` environment variable, which updates the value of ``site.USER_BASE``.

To install "SomePackage" into an environment with site.USER_BASE customized to '/myappenv', do the following::

    export PYTHONUSERBASE=/myappenv
    pip install --user SomePackage


``pip install --user`` follows four rules:

#. When globally installed packages are on the python path, and they *conflict*
   with the installation requirements, they are ignored, and *not*
   uninstalled.
#. When globally installed packages are on the python path, and they *satisfy*
   the installation requirements, pip does nothing, and reports that
   requirement is satisfied (similar to how global packages can satisfy
   requirements when installing packages in a ``--system-site-packages``
   virtualenv).
#. pip will not perform a ``--user`` install in a ``--no-site-packages``
   virtualenv (i.e. the default kind of virtualenv), due to the user site not
   being on the python path.  The installation would be pointless.
#. In a ``--system-site-packages`` virtualenv, pip will not install a package
   that conflicts with a package in the virtualenv site-packages.  The --user
   installation would lack sys.path precedence and be pointless.


To make the rules clearer, here are some examples:


From within a ``--no-site-packages`` virtualenv (i.e. the default kind)::

  $ pip install --user SomePackage
  Can not perform a '--user' install. User site-packages are not visible in this virtualenv.


From within a ``--system-site-packages`` virtualenv where ``SomePackage==0.3`` is already installed in the virtualenv::

  $ pip install --user SomePackage==0.4
  Will not install to the user site because it will lack sys.path precedence


From within a real python, where ``SomePackage`` is *not* installed globally::

  $ pip install --user SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, but is *not* the latest version::

  $ pip install --user SomePackage
  [...]
  Requirement already satisfied (use --upgrade to upgrade)

  $ pip install --user --upgrade SomePackage
  [...]
  Successfully installed SomePackage


From within a real python, where ``SomePackage`` *is* installed globally, and is the latest version::

  $ pip install --user SomePackage
  [...]
  Requirement already satisfied (use --upgrade to upgrade)

  $ pip install --user --upgrade SomePackage
  [...]
  Requirement already up-to-date: SomePackage

  # force the install
  $ pip install --user --ignore-installed SomePackage
  [...]
  Successfully installed SomePackage



Controlling setup_requires
**************************

Setuptools offers the ``setup_requires``
`setup() keyword <http://pythonhosted.org/setuptools/setuptools.html#new-and-changed-setup-keywords>`_
for specifying dependencies that need to be present in order for the `setup.py` script to run.
Internally, Setuptools uses ``easy_install`` to fulfill these dependencies.

pip has no way to control how these dependencies are located.
None of the :ref:`Package Index Options <Package Index Options>` have an effect.

The solution is to configure a "system" or "personal"
`Distutils configuration file <http://docs.python.org/2/install/index.html#distutils-configuration-files>`_
to manage the fulfillment.

For example, to have the dependency located at an alternate index, add this:

::

  [easy_install]
  index_url = https://my.index-mirror.com

To have the dependency located from a local directory and not crawl PyPI, add this:

::

  [easy_install]
  allow_hosts = ''
  find_links = file:///path/to/local/archives


Upgrading from distribute to setuptools
***************************************

`distribute`_ has now been merged into `setuptools`_, and it is recommended to upgrade to setuptools when possible.

To upgrade from `distribute`_ to `setuptools`_ using pip, run::

  pip install --upgrade setuptools

"ImportError: No module named setuptools"
-----------------------------------------

Although using the upgrade command above works in isolation, it's possible to get
"ImportError: No module named setuptools" when using pip<1.4 to upgrade a
package that depends on setuptools or distribute.

e.g. when running a command like this:  `pip install --upgrade pyramid`

Solution
~~~~~~~~

To prevent the problem in *new* environments (that aren't broken yet):

* Option 1:

 * *First* run `pip install -U setuptools`,
 * *Then* run the command to upgrade your package (e.g. `pip install --upgrade pyramid`)

* Option 2:

 * Upgrade pip using :ref:`get-pip <get-pip>`
 * *Then* run the command to upgrade your package (e.g. `pip install --upgrade pyramid`)

To fix the problem once it's occurred, you'll need to manually install the new
setuptools, then rerun the upgrade that failed.

1. Download `ez_setup.py` (https://bitbucket.org/pypa/setuptools/downloads/ez_setup.py)
2. Run `python ez_setup.py`
3. Then rerun your upgrade (e.g. `pip install --upgrade pyramid`)


Cause
~~~~~

distribute-0.7.3 is just an empty wrapper that only serves to require the new
setuptools (setuptools>=0.7) so that it will be installed. (If you don't know
yet, the "new setuptools" is a merge of distribute and setuptools back into one
project).

distribute-0.7.3 does its job well, when the upgrade is done in isolation.
E.g. if you're currently on distribute-0.6.X, then running `pip install -U
setuptools` works fine to upgrade you to setuptools>=0.7.

The problem occurs when:

1. you are currently using an older distribute (i.e. 0.6.X)
2. and you try to use pip to upgrade a package that *depends* on setuptools or
   distribute.

As part of the upgrade process, pip builds an install list that ends up
including distribute-0.7.3 and setuptools>=0.7 , but they can end up being
separated by other dependencies in the list, so what can happen is this:

1.  pip uninstalls the existing distribute
2.  pip installs distribute-0.7.3 (which has no importable setuptools, that pip
    *needs* internally to function)
3.  pip moves on to install another dependency (before setuptools>=0.7) and is
    unable to proceed without the setuptools package

Note that pip v1.4 has fixes to prevent this.  distribute-0.7.3 (or
setuptools>=0.7) by themselves cannot prevent this kind of problem.

.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute
.. _PyPI: https://pypi.python.org
