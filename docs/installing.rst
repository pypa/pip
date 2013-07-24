.. _`Installation`:

Installation
============

.. warning::

    Prior to version 1.3, pip did not use SSL for downloading packages from PyPI, and thus left
    users more vulnerable to security threats. We advise installing at least version 1.3.
    If you're using `virtualenv <http://www.virtualenv.org>`_ to install pip, we advise installing
    at least version 1.9, which contains pip version 1.3.


Python & OS Support
-------------------

pip v1.4 works with CPython versions 2.6, 2.7, 3.1, 3.2, 3.3 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through v1.1.



Using virtualenv
----------------

If you already have virtualenv installed, then the easiest way to use pip is through `virtualenv
<http://www.virtualenv.org>`_, since every virtualenv has pip (and its dependencies) installed into it
automatically.

This does not require root access or modify your system Python
installation. For instance::

    $ virtualenv my_env
    $ . my_env/bin/activate
    (my_env)$ pip install SomePackage

When used in this manner, pip will only affect the active virtual environment.

To ensure the virtual environment includes the latest version of pip, run::

    $ pip install --upgrade pip

If the ``virtualenv`` command above doesn't work, then you will need to get it onto
your system first. This is covered in the next section.


Bootstrapping pip and virtualenv
--------------------------------

Perhaps confusingly, the easiest way to install virtualenv is to use pip!::

    $ pip install virtualenv

However, that doesn't help in this case, since pip isn't currently available. That
means it is necessary to bootstrap pip onto the system using some other tools.

.. note::

   The following instructions recommend granting some unreadable, unsigned code that
   you downloaded from the internet elevated privileges. This is, to say the least,
   almost always a bad idea.

   We're working on improving the situation so you don't need to do that, but, for
   now, these are the best bootstrapping instructions we have to offer. If you don't
   understand this warning, don't follow the instructions below until you've found
   someone you trust to explain it to you.


Linux
~~~~~

On Linux, pip and virtualenv will generally be available through the system package manager.
Recent versions of common desktop Linux distributions include suitably recent versions of
both, so for global installation into the system Python, it is recommended to install the
system package manager versions, and then use virtualenv to create a separate virtual
environment as described above.

On Debian and Ubuntu::

   $ sudo apt-get install python-pip python-virtualenv

On Fedora::

   $ sudo yum install python-pip python-virtualenv

While these may not always be the most up to date versions of ``pip``, following the
instructions in the previous section should ensure that the latest version is
installed into virtual environments without risking any adverse effects on the
system installation of Python.

.. note::

   If you want to ensure the system installation of Python has the latest version of
   pip installed, the instructions given for Mac OS X and other *nix systems also
   work on Linux. Just be aware that the system package manager may complain about
   it later.


Mac OS X (and other *nix systems)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following commands will install setuptools and pip into the system installation of
Python::

   $ curl -O https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
   $ sudo python ez_setup.py
   $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
   $ sudo python get-pip.py

Once you have pip installed, you can use it to retrieve virtualenv::

   $ sudo pip install virtualenv

And then proceed to the virtualenv instructions shown above.


Windows
~~~~~~~

The bootstrapping process on Windows is more complex than it is on other
platforms, since there is no system package manager, no ``curl``
tool to easily download the bootstrap script and the exact operations
needed to save the file will depend on your choice of browser (we'll
at least give some hints for Internet Explorer and Firefox).


1. If you don't have Python 3.3 or later installed, install the Python
   Launcher for Windows from https://bitbucket.org/pypa/pylauncher/downloads
   (get launchwin.msi for 32-bit Windows, or launchwin.amd64.msi for 64-bit
   Windows). This will add the "py" command to your command line environment,
   which we're going to need later (Python 3.3 offers this command by default)
2. Open your preferred browser and go to
   https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
3. This should open as a text file in the browser (showing a lot of unreadable
   characters - those are actually an embedded copy of pip that will be
   used to retrieve the copy of pip that will actually be installed)
4. Save this page locally. It doesn't really matter where you
   save it, but remember where it was so you can find it later. Both Firefox
   and Internet Explorer will want to add another extension. Since Internet
   Explorer doesn't even provide a way to skip adding an extension, we'll let
   them add it and rename the file in the next step.
5. Find the downloaded file in Windows Explorer and edit the filename to ensure
   it is exactly "ex_setup.py". (You may need to go into
   "Organize->Folder and Search options->View" and uncheck "Hide extensions for
   known file types" before Windows will let you do this, and even then it will
   complain about changing the file extension)
6. This is probably a good time to scan the downloaded file with your virus
   scanner to help ensure we're not trying to get you to install malware :)
7. Repeat steps 2 to 6, only with the URL
   https://raw.github.com/pypa/pip/master/contrib/get-pip.py and the local file
   name "get-pip.py"
8. Open a command prompt and switch to the directory where the files were downloaded
9. Run "py ez_setup.py"
10. Run "py get-pip.py"

Addendum if you have Python 2 and 3 installed in parallel. Also run (since the
above commands will install to the Python 2 installation by default):

11. Run "py -3 ez_setup.py"
12. Run "py -3 get-pip.py"



Installing pip from source
--------------------------



Note: the instructions below won't work on Windows. Windows users are strongly encouraged
to use the bootstrapping described above.

.. _`Installation Requirements`:

Requirements
++++++++++++

pip requires `setuptools`_.

.. warning::

    As of pip 1.4, pip recommends `setuptools`_ >=0.8, not `distribute`_ (a
    fork of setuptools) and the wheel support *requires* `setuptools`_ >=0.8.
    `setuptools`_ and `distribute`_ are now merged back together as
    "setuptools".

For details on installing setuptools from scratch, see the install instructions
on the `setuptools pypi page <https://pypi.python.org/pypi/setuptools>`_

If you already have `setuptools`_ or `distribute`_ (and pip), you can upgrade
like so::

    pip install --upgrade setuptools

If you had distribute before, this will upgrade you to distribute-0.7.X, which
is just a wrapper, that depends on setuptools. The end result will be that you
have distribute-0.7.X (which does nothing) *and* the latest setuptools
installed.


.. _setuptools: https://pypi.python.org/pypi/setuptools
.. _distribute: https://pypi.python.org/pypi/distribute

Once a suitable version of setuptools is available, pip can be installed
from source::

 $ curl -O https://pypi.python.org/packages/source/p/pip/pip-X.X.tar.gz
 $ tar xvfz pip-X.X.tar.gz
 $ cd pip-X.X
 $ sudo python setup.py install

Since even these more explicit instructions still involve running an arbitrary
script from the internet with elevated privileges, the user level bootstrapping
described above is *strongly* recommended.
