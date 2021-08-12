.. note

    You should *NOT* be adding new change log entries to this file, this
    file is managed by towncrier. You *may* edit previous change logs to
    fix problems like typo corrections or such.

    To add a new change log entry, please see
        https://pip.pypa.io/en/latest/development/contributing/#news-entries


.. towncrier release notes start

21.2.4 (2021-08-12)
===================

Bug Fixes
---------

- Fix 3.6.0 compatibility in link comparison logic. (`#10280 <https://github.com/pypa/pip/issues/10280>`_)


21.2.3 (2021-08-06)
===================

Bug Fixes
---------

- Modify the ``sysconfig.get_preferred_scheme`` function check to be
  compatible with CPython 3.10’s alphareleases. (`#10252 <https://github.com/pypa/pip/issues/10252>`_)


21.2.2 (2021-07-31)
===================

Bug Fixes
---------

- New resolver: When a package is specified with extras in constraints, and with
  extras in non-constraint requirements, the resolver now correctly identifies the
  constraint's existence and avoids backtracking. (`#10233 <https://github.com/pypa/pip/issues/10233>`_)


21.2.1 (2021-07-25)
===================

Process
-------

- The source distribution re-installation feature removal has been delayed to 21.3.


21.2 (2021-07-24)
=================

Process
-------

- ``pip freeze``, ``pip list``, and ``pip show`` no longer normalize underscore
  (``_``) in distribution names to dash (``-``). This is a side effect of the
  migration to ``importlib.metadata``, since the underscore-dash normalization
  behavior is non-standard and specific to setuptools. This should not affect
  other parts of pip (for example, when feeding the ``pip freeze`` result back
  into ``pip install``) since pip internally performs standard PEP 503
  normalization independently to setuptools.

Deprecations and Removals
-------------------------

- Git version parsing is now done with regular expression to prepare for the
  pending upstream removal of non-PEP-440 version parsing logic. (`#10117 <https://github.com/pypa/pip/issues/10117>`_)
- Re-enable the "Value for ... does not match" location warnings to field a new
  round of feedback for the ``distutils``-``sysconfig`` transition. (`#10151 <https://github.com/pypa/pip/issues/10151>`_)
- Remove deprecated ``--find-links`` option in ``pip freeze`` (`#9069 <https://github.com/pypa/pip/issues/9069>`_)

Features
--------

- New resolver: Loosen URL comparison logic when checking for direct URL reference
  equivalency. The logic includes the following notable characteristics:

  * The authentication part of the URL is explicitly ignored.
  * Most of the fragment part, including ``egg=``, is explicitly ignored. Only
    ``subdirectory=`` and hash values (e.g. ``sha256=``) are kept.
  * The query part of the URL is parsed to allow ordering differences. (`#10002 <https://github.com/pypa/pip/issues/10002>`_)
- Support TOML v1.0.0 syntax in ``pyproject.toml``. (`#10034 <https://github.com/pypa/pip/issues/10034>`_)
- Added a warning message for errors caused due to Long Paths being disabled on Windows. (`#10045 <https://github.com/pypa/pip/issues/10045>`_)
- Change the encoding of log file from default text encoding to UTF-8. (`#10071 <https://github.com/pypa/pip/issues/10071>`_)
- Log the resolved commit SHA when installing a package from a Git repository. (`#10149 <https://github.com/pypa/pip/issues/10149>`_)
- Add a warning when passing an invalid requirement to ``pip uninstall``. (`#4958 <https://github.com/pypa/pip/issues/4958>`_)
- Add new subcommand ``pip index`` used to interact with indexes, and implement
  ``pip index version`` to list available versions of a package. (`#7975 <https://github.com/pypa/pip/issues/7975>`_)
- When pip is asked to uninstall a project without the dist-info/RECORD file
  it will no longer traceback with FileNotFoundError,
  but it will provide a better error message instead, such as::

      ERROR: Cannot uninstall foobar 0.1, RECORD file not found. You might be able to recover from this via: 'pip install --force-reinstall --no-deps foobar==0.1'.

  When dist-info/INSTALLER is present and contains some useful information, the info is included in the error message instead::

      ERROR: Cannot uninstall foobar 0.1, RECORD file not found. Hint: The package was installed by rpm.

  (`#8954 <https://github.com/pypa/pip/issues/8954>`_)
- Add an additional level of verbosity. ``--verbose`` (and the shorthand ``-v``) now
  contains significantly less output, and users that need complete full debug-level output
  should pass it twice (``--verbose --verbose`` or ``-vv``). (`#9450 <https://github.com/pypa/pip/issues/9450>`_)
- New resolver: The order of dependencies resolution has been tweaked to traverse
  the dependency graph in a more breadth-first approach. (`#9455 <https://github.com/pypa/pip/issues/9455>`_)
- Make "yes" the default choice in ``pip uninstall``'s prompt. (`#9686 <https://github.com/pypa/pip/issues/9686>`_)
- Add a special error message when users forget the ``-r`` flag when installing. (`#9915 <https://github.com/pypa/pip/issues/9915>`_)
- New resolver: A distribution's ``Requires-Python`` metadata is now checked
  before its Python dependencies. This makes the resolver fail quicker when
  there's an interpreter version conflict. (`#9925 <https://github.com/pypa/pip/issues/9925>`_)
- Suppress "not on PATH" warning when ``--prefix`` is given. (`#9931 <https://github.com/pypa/pip/issues/9931>`_)
- Include ``rustc`` version in pip's ``User-Agent``, when the system has ``rustc``. (`#9987 <https://github.com/pypa/pip/issues/9987>`_)

Bug Fixes
---------

- Update vendored six to 1.16.0 and urllib3 to 1.26.5 (`#10043 <https://github.com/pypa/pip/issues/10043>`_)
- Correctly allow PEP 517 projects to be detected without warnings in ``pip freeze``. (`#10080 <https://github.com/pypa/pip/issues/10080>`_)
- Strip leading slash from a ``file://`` URL built from an path with the Windows
  drive notation. This fixes bugs where the ``file://`` URL cannot be correctly
  used as requirement, constraint, or index URLs on Windows. (`#10115 <https://github.com/pypa/pip/issues/10115>`_)
- New resolver: URL comparison logic now treats ``file://localhost/`` and
  ``file:///`` as equivalent to conform to RFC 8089. (`#10162 <https://github.com/pypa/pip/issues/10162>`_)
- Prefer credentials from the URL over the previously-obtained credentials from URLs of the same domain, so it is possible to use different credentials on the same index server for different ``--extra-index-url`` options. (`#3931 <https://github.com/pypa/pip/issues/3931>`_)
- Fix extraction of files with utf-8 encoded paths from tars. (`#7667 <https://github.com/pypa/pip/issues/7667>`_)
- Skip distutils configuration parsing on encoding errors. (`#8931 <https://github.com/pypa/pip/issues/8931>`_)
- New resolver: Detect an unnamed requirement is user-specified (by building its
  metadata for the project name) so it can be correctly ordered in the resolver. (`#9204 <https://github.com/pypa/pip/issues/9204>`_)
- Fix :ref:`pip freeze` to output packages :ref:`installed from git <vcs support>`
  in the correct ``git+protocol://git.example.com/MyProject#egg=MyProject`` format
  rather than the old and no longer supported ``git+git@`` format. (`#9822 <https://github.com/pypa/pip/issues/9822>`_)
- Fix warnings about install scheme selection for Python framework builds
  distributed by Apple's Command Line Tools. (`#9844 <https://github.com/pypa/pip/issues/9844>`_)
- Relax interpreter detection to quelch a location mismatch warning where PyPy
  is deliberately breaking backwards compatibility. (`#9845 <https://github.com/pypa/pip/issues/9845>`_)

Vendored Libraries
------------------

- Upgrade certifi to 2021.05.30.
- Upgrade idna to 3.2.
- Upgrade packaging to 21.0
- Upgrade requests to 2.26.0.
- Upgrade resolvelib to 0.7.1.
- Upgrade urllib3 to 1.26.6.


21.1.3 (2021-06-26)
===================

Bug Fixes
---------

- Remove unused optional ``tornado`` import in vendored ``tenacity`` to prevent old versions of Tornado from breaking pip. (`#10020 <https://github.com/pypa/pip/issues/10020>`_)
- Require ``setup.cfg``-only projects to be built via PEP 517, by requiring an explicit dependency on setuptools declared in pyproject.toml. (`#10031 <https://github.com/pypa/pip/issues/10031>`_)


21.1.2 (2021-05-23)
===================

Bug Fixes
---------

- New resolver: Correctly exclude an already installed package if its version is
  known to be incompatible to stop the dependency resolution process with a clear
  error message. (`#9841 <https://github.com/pypa/pip/issues/9841>`_)
- Allow ZIP to archive files with timestamps earlier than 1980. (`#9910 <https://github.com/pypa/pip/issues/9910>`_)
- Emit clearer error message when a project root does not contain either
  ``pyproject.toml``, ``setup.py`` or ``setup.cfg``. (`#9944 <https://github.com/pypa/pip/issues/9944>`_)
- Fix detection of existing standalone pip instance for PEP 517 builds. (`#9953 <https://github.com/pypa/pip/issues/9953>`_)


21.1.1 (2021-04-30)
===================

Deprecations and Removals
-------------------------

- Temporarily set the new "Value for ... does not match" location warnings level
  to *DEBUG*, to hide them from casual users. This prepares pip 21.1 for CPython
  inclusion, while pip maintainers digest the first intake of location mismatch
  issues for the ``distutils``-``sysconfig`` transition. (`#9912 <https://github.com/pypa/pip/issues/9912>`_)

Bug Fixes
---------

- This change fixes a bug on Python <=3.6.1 with a Typing feature added in 3.6.2 (`#9831 <https://github.com/pypa/pip/issues/9831>`_)
- Fix compatibility between distutils and sysconfig when the project name is unknown outside of a virtual environment. (`#9838 <https://github.com/pypa/pip/issues/9838>`_)
- Fix Python 3.6 compatibility when a PEP 517 build requirement itself needs to be
  built in an isolated environment. (`#9878 <https://github.com/pypa/pip/issues/9878>`_)


21.1 (2021-04-24)
=================

Process
-------

- Start installation scheme migration from ``distutils`` to ``sysconfig``. A
  warning is implemented to detect differences between the two implementations to
  encourage user reports, so we can avoid breakages before they happen.

Features
--------

- Add the ability for the new resolver to process URL constraints. (`#8253 <https://github.com/pypa/pip/issues/8253>`_)
- Add a feature ``--use-feature=in-tree-build`` to build local projects in-place
  when installing. This is expected to become the default behavior in pip 21.3;
  see `Installing from local packages <https://pip.pypa.io/en/stable/user_guide/#installing-from-local-packages>`_
  for more information. (`#9091 <https://github.com/pypa/pip/issues/9091>`_)
- Bring back the "(from versions: ...)" message, that was shown on resolution failures. (`#9139 <https://github.com/pypa/pip/issues/9139>`_)
- Add support for editable installs for project with only setup.cfg files. (`#9547 <https://github.com/pypa/pip/issues/9547>`_)
- Improve performance when picking the best file from indexes during ``pip install``. (`#9748 <https://github.com/pypa/pip/issues/9748>`_)
- Warn instead of erroring out when doing a PEP 517 build in presence of
  ``--build-option``. Warn when doing a PEP 517 build in presence of
  ``--global-option``. (`#9774 <https://github.com/pypa/pip/issues/9774>`_)

Bug Fixes
---------

- Fixed ``--target`` to work with ``--editable`` installs. (`#4390 <https://github.com/pypa/pip/issues/4390>`_)
- Add a warning, discouraging the usage of pip as root, outside a virtual environment. (`#6409 <https://github.com/pypa/pip/issues/6409>`_)
- Ignore ``.dist-info`` directories if the stem is not a valid Python distribution
  name, so they don't show up in e.g. ``pip freeze``. (`#7269 <https://github.com/pypa/pip/issues/7269>`_)
- Only query the keyring for URLs that actually trigger error 401.
  This prevents an unnecessary keyring unlock prompt on every pip install
  invocation (even with default index URL which is not password protected). (`#8090 <https://github.com/pypa/pip/issues/8090>`_)
- Prevent packages already-installed alongside with pip to be injected into an
  isolated build environment during build-time dependency population. (`#8214 <https://github.com/pypa/pip/issues/8214>`_)
- Fix ``pip freeze`` permission denied error in order to display an understandable error message and offer solutions. (`#8418 <https://github.com/pypa/pip/issues/8418>`_)
- Correctly uninstall script files (from setuptools' ``scripts`` argument), when installed with ``--user``. (`#8733 <https://github.com/pypa/pip/issues/8733>`_)
- New resolver: When a requirement is requested both via a direct URL
  (``req @ URL``) and via version specifier with extras (``req[extra]``), the
  resolver will now be able to use the URL to correctly resolve the requirement
  with extras. (`#8785 <https://github.com/pypa/pip/issues/8785>`_)
- New resolver: Show relevant entries from user-supplied constraint files in the
  error message to improve debuggability. (`#9300 <https://github.com/pypa/pip/issues/9300>`_)
- Avoid parsing version to make the version check more robust against lousily
  debundled downstream distributions. (`#9348 <https://github.com/pypa/pip/issues/9348>`_)
- ``--user`` is no longer suggested incorrectly when pip fails with a permission
  error in a virtual environment. (`#9409 <https://github.com/pypa/pip/issues/9409>`_)
- Fix incorrect reporting on ``Requires-Python`` conflicts. (`#9541 <https://github.com/pypa/pip/issues/9541>`_)
- Make wheel compatibility tag preferences more important than the build tag (`#9565 <https://github.com/pypa/pip/issues/9565>`_)
- Fix pip to work with warnings converted to errors. (`#9779 <https://github.com/pypa/pip/issues/9779>`_)
- **SECURITY**: Stop splitting on unicode separators in git references,
  which could be maliciously used to install a different revision on the
  repository. (`#9827 <https://github.com/pypa/pip/issues/9827>`_)

Vendored Libraries
------------------

- Update urllib3 to 1.26.4 to fix CVE-2021-28363
- Remove contextlib2.
- Upgrade idna to 3.1
- Upgrade pep517 to 0.10.0
- Upgrade vendored resolvelib to 0.7.0.
- Upgrade tenacity to 7.0.0

Improved Documentation
----------------------

- Update "setuptools extras" link to match upstream. (`#4822829F-6A45-4202-87BA-A80482DF6D4E <https://github.com/pypa/pip/issues/4822829F-6A45-4202-87BA-A80482DF6D4E>`_)
- Improve SSL Certificate Verification docs and ``--cert`` help text. (`#6720 <https://github.com/pypa/pip/issues/6720>`_)
- Add a section in the documentation to suggest solutions to the ``pip freeze`` permission denied issue. (`#8418 <https://github.com/pypa/pip/issues/8418>`_)
- Add warning about ``--extra-index-url`` and dependency confusion (`#9647 <https://github.com/pypa/pip/issues/9647>`_)
- Describe ``--upgrade-strategy`` and direct requirements explicitly; add a brief
  example. (`#9692 <https://github.com/pypa/pip/issues/9692>`_)


21.0.1 (2021-01-30)
===================

Bug Fixes
---------

- commands: debug: Use packaging.version.parse to compare between versions. (`#9461 <https://github.com/pypa/pip/issues/9461>`_)
- New resolver: Download and prepare a distribution only at the last possible
  moment to avoid unnecessary network access when the same version is already
  installed locally. (`#9516 <https://github.com/pypa/pip/issues/9516>`_)

Vendored Libraries
------------------

- Upgrade packaging to 20.9


21.0 (2021-01-23)
=================

Deprecations and Removals
-------------------------

- Drop support for Python 2. (`#6148 <https://github.com/pypa/pip/issues/6148>`_)
- Remove support for legacy wheel cache entries that were created with pip
  versions older than 20.0. (`#7502 <https://github.com/pypa/pip/issues/7502>`_)
- Remove support for VCS pseudo URLs editable requirements. It was emitting
  deprecation warning since version 20.0. (`#7554 <https://github.com/pypa/pip/issues/7554>`_)
- Modernise the codebase after Python 2. (`#8802 <https://github.com/pypa/pip/issues/8802>`_)
- Drop support for Python 3.5. (`#9189 <https://github.com/pypa/pip/issues/9189>`_)
- Remove the VCS export feature that was used only with editable VCS
  requirements and had correctness issues. (`#9338 <https://github.com/pypa/pip/issues/9338>`_)

Features
--------

- Add ``--ignore-requires-python`` support to pip download. (`#1884 <https://github.com/pypa/pip/issues/1884>`_)
- New resolver: Error message shown when a wheel contains inconsistent metadata
  is made more helpful by including both values from the file name and internal
  metadata. (`#9186 <https://github.com/pypa/pip/issues/9186>`_)

Bug Fixes
---------

- Fix a regression that made ``pip wheel`` do a VCS export instead of a VCS clone
  for editable requirements. This broke VCS requirements that need the VCS
  information to build correctly. (`#9273 <https://github.com/pypa/pip/issues/9273>`_)
- Fix ``pip download`` of editable VCS requirements that need VCS information
  to build correctly. (`#9337 <https://github.com/pypa/pip/issues/9337>`_)

Vendored Libraries
------------------

- Upgrade msgpack to 1.0.2.
- Upgrade requests to 2.25.1.

Improved Documentation
----------------------

- Render the unreleased pip version change notes on the news page in docs. (`#9172 <https://github.com/pypa/pip/issues/9172>`_)
- Fix broken email link in docs feedback banners. (`#9343 <https://github.com/pypa/pip/issues/9343>`_)


20.3.4 (2021-01-23)
===================

Features
--------

- ``pip wheel`` now verifies the built wheel contains valid metadata, and can be
  installed by a subsequent ``pip install``. This can be disabled with
  ``--no-verify``. (`#9206 <https://github.com/pypa/pip/issues/9206>`_)
- Improve presentation of XMLRPC errors in pip search. (`#9315 <https://github.com/pypa/pip/issues/9315>`_)

Bug Fixes
---------

- Fixed hanging VCS subprocess calls when the VCS outputs a large amount of data
  on stderr. Restored logging of VCS errors that was inadvertently removed in pip
  20.2. (`#8876 <https://github.com/pypa/pip/issues/8876>`_)
- Fix error when an existing incompatibility is unable to be applied to a backtracked state. (`#9180 <https://github.com/pypa/pip/issues/9180>`_)
- New resolver: Discard a faulty distribution, instead of quitting outright.
  This implementation is taken from 20.2.2, with a fix that always makes the
  resolver iterate through candidates from indexes lazily, to avoid downloading
  candidates we do not need. (`#9203 <https://github.com/pypa/pip/issues/9203>`_)
- New resolver: Discard a source distribution if it fails to generate metadata,
  instead of quitting outright. This implementation is taken from 20.2.2, with a
  fix that always makes the resolver iterate through candidates from indexes
  lazily, to avoid downloading candidates we do not need. (`#9246 <https://github.com/pypa/pip/issues/9246>`_)

Vendored Libraries
------------------

- Upgrade resolvelib to 0.5.4.


20.3.3 (2020-12-15)
===================

Bug Fixes
---------

- Revert "Skip candidate not providing valid metadata", as that caused pip to be overeager about downloading from the package index. (`#9264 <https://github.com/pypa/pip/issues/9264>`_)


20.3.2 (2020-12-15)
===================

Features
--------

- New resolver: Resolve direct and pinned (``==`` or ``===``) requirements first
  to improve resolver performance. (`#9185 <https://github.com/pypa/pip/issues/9185>`_)
- Add a mechanism to delay resolving certain packages, and use it for setuptools. (`#9249 <https://github.com/pypa/pip/issues/9249>`_)

Bug Fixes
---------

- New resolver: The "Requirement already satisfied" log is not printed only once
  for each package during resolution. (`#9117 <https://github.com/pypa/pip/issues/9117>`_)
- Fix crash when logic for redacting authentication information from URLs
  in ``--help`` is given a list of strings, instead of a single string. (`#9191 <https://github.com/pypa/pip/issues/9191>`_)
- New resolver: Correctly implement PEP 592. Do not return yanked versions from
  an index, unless the version range can only be satisfied by yanked candidates. (`#9203 <https://github.com/pypa/pip/issues/9203>`_)
- New resolver: Make constraints also apply to package variants with extras, so
  the resolver correctly avoids backtracking on them. (`#9232 <https://github.com/pypa/pip/issues/9232>`_)
- New resolver: Discard a candidate if it fails to provide metadata from source,
  or if the provided metadata is inconsistent, instead of quitting outright. (`#9246 <https://github.com/pypa/pip/issues/9246>`_)

Vendored Libraries
------------------

- Update vendoring to 20.8

Improved Documentation
----------------------

- Update documentation to reflect that pip still uses legacy resolver by default in Python 2 environments. (`#9269 <https://github.com/pypa/pip/issues/9269>`_)


20.3.1 (2020-12-03)
===================

Deprecations and Removals
-------------------------

- The --build-dir option has been restored as a no-op, to soften the transition
  for tools that still used it. (`#9193 <https://github.com/pypa/pip/issues/9193>`_)


20.3 (2020-11-30)
=================

Deprecations and Removals
-------------------------

- Remove --unstable-feature flag as it has been deprecated. (`#9133 <https://github.com/pypa/pip/issues/9133>`_)

Features
--------

- Add support for :pep:`600`: Future 'manylinux' Platform Tags for Portable Linux Built Distributions. (`#9077 <https://github.com/pypa/pip/issues/9077>`_)
- The new resolver now resolves packages in a deterministic order. (`#9100 <https://github.com/pypa/pip/issues/9100>`_)
- Add support for MacOS Big Sur compatibility tags. (`#9138 <https://github.com/pypa/pip/issues/9138>`_)

Bug Fixes
---------

- New Resolver: Rework backtracking and state management, to avoid getting stuck in an infinite loop. (`#9011 <https://github.com/pypa/pip/issues/9011>`_)
- New resolver: Check version equality with ``packaging.version`` to avoid edge
  cases if a wheel used different version normalization logic in its filename
  and metadata. (`#9083 <https://github.com/pypa/pip/issues/9083>`_)
- New resolver: Show each requirement in the conflict error message only once to reduce cluttering. (`#9101 <https://github.com/pypa/pip/issues/9101>`_)
- Fix a regression that made ``pip wheel`` generate zip files of editable
  requirements in the wheel directory. (`#9122 <https://github.com/pypa/pip/issues/9122>`_)
- Fix ResourceWarning in VCS subprocesses (`#9156 <https://github.com/pypa/pip/issues/9156>`_)
- Redact auth from URL in help message. (`#9160 <https://github.com/pypa/pip/issues/9160>`_)
- New Resolver: editable installations are done, regardless of whether
  the already-installed distribution is editable. (`#9169 <https://github.com/pypa/pip/issues/9169>`_)

Vendored Libraries
------------------

- Upgrade certifi to 2020.11.8
- Upgrade colorama to 0.4.4
- Upgrade packaging to 20.7
- Upgrade pep517 to 0.9.1
- Upgrade requests to 2.25.0
- Upgrade resolvelib to 0.5.3
- Upgrade toml to 0.10.2
- Upgrade urllib3 to 1.26.2

Improved Documentation
----------------------

- Add a section to the User Guide to cover backtracking during dependency resolution. (`#9039 <https://github.com/pypa/pip/issues/9039>`_)
- Reorder and revise installation instructions to make them easier to follow. (`#9131 <https://github.com/pypa/pip/issues/9131>`_)


20.3b1 (2020-10-31)
===================

Deprecations and Removals
-------------------------

- ``pip freeze`` will stop filtering the ``pip``, ``setuptools``, ``distribute`` and ``wheel`` packages from ``pip freeze`` output in a future version.
  To keep the previous behavior, users should use the new ``--exclude`` option. (`#4256 <https://github.com/pypa/pip/issues/4256>`_)
- Deprecate support for Python 3.5 (`#8181 <https://github.com/pypa/pip/issues/8181>`_)
- Document that certain removals can be fast tracked. (`#8417 <https://github.com/pypa/pip/issues/8417>`_)
- Document that Python versions are generally supported until PyPI usage falls below 5%. (`#8927 <https://github.com/pypa/pip/issues/8927>`_)
- Deprecate ``--find-links`` option in ``pip freeze`` (`#9069 <https://github.com/pypa/pip/issues/9069>`_)

Features
--------

- Add ``--exclude`` option to ``pip freeze`` and ``pip list`` commands to explicitly exclude packages from the output. (`#4256 <https://github.com/pypa/pip/issues/4256>`_)
- Allow multiple values for --abi and --platform. (`#6121 <https://github.com/pypa/pip/issues/6121>`_)
- Add option ``--format`` to subcommand ``list`` of ``pip  cache``, with ``abspath`` choice to output the full path of a wheel file. (`#8355 <https://github.com/pypa/pip/issues/8355>`_)
- Improve error message friendliness when an environment has packages with
  corrupted metadata. (`#8676 <https://github.com/pypa/pip/issues/8676>`_)
- Make the ``setup.py install`` deprecation warning less noisy. We warn only
  when ``setup.py install`` succeeded and ``setup.py bdist_wheel`` failed, as
  situations where both fails are most probably irrelevant to this deprecation. (`#8752 <https://github.com/pypa/pip/issues/8752>`_)
- Check the download directory for existing wheels to possibly avoid
  fetching metadata when the ``fast-deps`` feature is used with
  ``pip wheel`` and ``pip download``. (`#8804 <https://github.com/pypa/pip/issues/8804>`_)
- When installing a git URL that refers to a commit that is not available locally
  after git clone, attempt to fetch it from the remote. (`#8815 <https://github.com/pypa/pip/issues/8815>`_)
- Include http subdirectory in ``pip cache info`` and ``pip cache purge`` commands. (`#8892 <https://github.com/pypa/pip/issues/8892>`_)
- Cache package listings on index packages so they are guaranteed to stay stable
  during a pip command session. This also improves performance when a index page
  is accessed multiple times during the command session. (`#8905 <https://github.com/pypa/pip/issues/8905>`_)
- New resolver: Tweak resolution logic to improve user experience when
  user-supplied requirements conflict. (`#8924 <https://github.com/pypa/pip/issues/8924>`_)
- Support Python 3.9. (`#8971 <https://github.com/pypa/pip/issues/8971>`_)
- Log an informational message when backtracking takes multiple rounds on a specific package. (`#8975 <https://github.com/pypa/pip/issues/8975>`_)
- Switch to the new dependency resolver by default. (`#9019 <https://github.com/pypa/pip/issues/9019>`_)
- Remove the ``--build-dir`` option, as per the deprecation. (`#9049 <https://github.com/pypa/pip/issues/9049>`_)

Bug Fixes
---------

- Propagate ``--extra-index-url`` from requirements file properly to session auth,
  so that keyring auth will work as expected. (`#8103 <https://github.com/pypa/pip/issues/8103>`_)
- Allow specifying verbosity and quiet level via configuration files
  and environment variables. Previously these options were treated as
  boolean values when read from there while through CLI the level can be
  specified. (`#8578 <https://github.com/pypa/pip/issues/8578>`_)
- Only converts Windows path to unicode on Python 2 to avoid regressions when a
  POSIX environment does not configure the file system encoding correctly. (`#8658 <https://github.com/pypa/pip/issues/8658>`_)
- List downloaded distributions before exiting ``pip download``
  when using the new resolver to make the behavior the same as
  that on the legacy resolver. (`#8696 <https://github.com/pypa/pip/issues/8696>`_)
- New resolver: Pick up hash declarations in constraints files and use them to
  filter available distributions. (`#8792 <https://github.com/pypa/pip/issues/8792>`_)
- Avoid polluting the destination directory by resolution artifacts
  when the new resolver is used for ``pip download`` or ``pip wheel``. (`#8827 <https://github.com/pypa/pip/issues/8827>`_)
- New resolver: If a package appears multiple times in user specification with
  different ``--hash`` options, only hashes that present in all specifications
  should be allowed. (`#8839 <https://github.com/pypa/pip/issues/8839>`_)
- Tweak the output during dependency resolution in the new resolver. (`#8861 <https://github.com/pypa/pip/issues/8861>`_)
- Correctly search for installed distributions in new resolver logic in order
  to not miss packages (virtualenv packages from system-wide-packages for example) (`#8963 <https://github.com/pypa/pip/issues/8963>`_)
- Do not fail in pip freeze when encountering a ``direct_url.json`` metadata file
  with editable=True. Render it as a non-editable ``file://`` URL until modern
  editable installs are standardized and supported. (`#8996 <https://github.com/pypa/pip/issues/8996>`_)

Vendored Libraries
------------------

- Fix devendoring instructions to explicitly state that ``vendor.txt`` should not be removed.
  It is mandatory for ``pip debug`` command.

Improved Documentation
----------------------

- Add documentation for '.netrc' support. (`#7231 <https://github.com/pypa/pip/issues/7231>`_)
- Add OS tabs for OS-specific commands. (`#7311 <https://github.com/pypa/pip/issues/7311>`_)
- Add note and example on keyring support for index basic-auth (`#8636 <https://github.com/pypa/pip/issues/8636>`_)
- Added initial UX feedback widgets to docs. (`#8783 <https://github.com/pypa/pip/issues/8783>`_, `#8848 <https://github.com/pypa/pip/issues/8848>`_)
- Add ux documentation (`#8807 <https://github.com/pypa/pip/issues/8807>`_)
- Update user docs to reflect new resolver as default in 20.3. (`#9044 <https://github.com/pypa/pip/issues/9044>`_)
- Improve migration guide to reflect changes in new resolver behavior. (`#9056 <https://github.com/pypa/pip/issues/9056>`_)


20.2.4 (2020-10-16)
===================

Deprecations and Removals
-------------------------

- Document that certain removals can be fast tracked. (`#8417 <https://github.com/pypa/pip/issues/8417>`_)
- Document that Python versions are generally supported until PyPI usage falls below 5%. (`#8927 <https://github.com/pypa/pip/issues/8927>`_)

Features
--------

- New resolver: Avoid accessing indexes when the installed candidate is preferred
  and considered good enough. (`#8023 <https://github.com/pypa/pip/issues/8023>`_)
- Improve error message friendliness when an environment has packages with
  corrupted metadata. (`#8676 <https://github.com/pypa/pip/issues/8676>`_)
- Cache package listings on index packages so they are guaranteed to stay stable
  during a pip command session. This also improves performance when a index page
  is accessed multiple times during the command session. (`#8905 <https://github.com/pypa/pip/issues/8905>`_)
- New resolver: Tweak resolution logic to improve user experience when
  user-supplied requirements conflict. (`#8924 <https://github.com/pypa/pip/issues/8924>`_)

Bug Fixes
---------

- New resolver: Correctly respect ``Requires-Python`` metadata to reject
  incompatible packages in ``--no-deps`` mode. (`#8758 <https://github.com/pypa/pip/issues/8758>`_)
- New resolver: Pick up hash declarations in constraints files and use them to
  filter available distributions. (`#8792 <https://github.com/pypa/pip/issues/8792>`_)
- New resolver: If a package appears multiple times in user specification with
  different ``--hash`` options, only hashes that present in all specifications
  should be allowed. (`#8839 <https://github.com/pypa/pip/issues/8839>`_)

Improved Documentation
----------------------

- Add ux documentation (`#8807 <https://github.com/pypa/pip/issues/8807>`_)


20.2.3 (2020-09-08)
===================

Deprecations and Removals
-------------------------

- Deprecate support for Python 3.5 (`#8181 <https://github.com/pypa/pip/issues/8181>`_)

Features
--------

- Make the ``setup.py install`` deprecation warning less noisy. We warn only
  when ``setup.py install`` succeeded and ``setup.py bdist_wheel`` failed, as
  situations where both fails are most probably irrelevant to this deprecation. (`#8752 <https://github.com/pypa/pip/issues/8752>`_)


20.2.2 (2020-08-11)
===================

Bug Fixes
---------

- Only attempt to use the keyring once and if it fails, don't try again.
  This prevents spamming users with several keyring unlock prompts when they
  cannot unlock or don't want to do so. (`#8090 <https://github.com/pypa/pip/issues/8090>`_)
- Fix regression that distributions in system site-packages are not correctly
  found when a virtual environment is configured with ``system-site-packages``
  on. (`#8695 <https://github.com/pypa/pip/issues/8695>`_)
- Disable caching for range requests, which causes corrupted wheels
  when pip tries to obtain metadata using the feature ``fast-deps``. (`#8701 <https://github.com/pypa/pip/issues/8701>`_, `#8716 <https://github.com/pypa/pip/issues/8716>`_)
- Always use UTF-8 to read ``pyvenv.cfg`` to match the built-in ``venv``. (`#8717 <https://github.com/pypa/pip/issues/8717>`_)
- 2020 Resolver: Correctly handle marker evaluation in constraints and exclude
  them if their markers do not match the current environment. (`#8724 <https://github.com/pypa/pip/issues/8724>`_)


20.2.1 (2020-08-04)
===================

Features
--------

- Ignore require-virtualenv in ``pip list`` (`#8603 <https://github.com/pypa/pip/issues/8603>`_)

Bug Fixes
---------

- Correctly find already-installed distributions with dot (``.``) in the name
  and uninstall them when needed. (`#8645 <https://github.com/pypa/pip/issues/8645>`_)
- Trace a better error message on installation failure due to invalid ``.data``
  files in wheels. (`#8654 <https://github.com/pypa/pip/issues/8654>`_)
- Fix SVN version detection for alternative SVN distributions. (`#8665 <https://github.com/pypa/pip/issues/8665>`_)
- New resolver: Correctly include the base package when specified with extras
  in ``--no-deps`` mode. (`#8677 <https://github.com/pypa/pip/issues/8677>`_)
- Use UTF-8 to handle ZIP archive entries on Python 2 according to PEP 427, so
  non-ASCII paths can be resolved as expected. (`#8684 <https://github.com/pypa/pip/issues/8684>`_)

Improved Documentation
----------------------

- Add details on old resolver deprecation and removal to migration documentation. (`#8371 <https://github.com/pypa/pip/issues/8371>`_)
- Fix feature flag name in docs. (`#8660 <https://github.com/pypa/pip/issues/8660>`_)


20.2 (2020-07-29)
=================

Deprecations and Removals
-------------------------

- Deprecate setup.py-based builds that do not generate an ``.egg-info`` directory. (`#6998 <https://github.com/pypa/pip/issues/6998>`_, `#8617 <https://github.com/pypa/pip/issues/8617>`_)
- Disallow passing install-location-related arguments in ``--install-options``. (`#7309 <https://github.com/pypa/pip/issues/7309>`_)
- Add deprecation warning for invalid requirements format "base>=1.0[extra]" (`#8288 <https://github.com/pypa/pip/issues/8288>`_)
- Deprecate legacy setup.py install when building a wheel failed for source
  distributions without pyproject.toml (`#8368 <https://github.com/pypa/pip/issues/8368>`_)
- Deprecate -b/--build/--build-dir/--build-directory. Its current behaviour is confusing
  and breaks in case different versions of the same distribution need to be built during
  the resolution process. Using the TMPDIR/TEMP/TMP environment variable, possibly
  combined with --no-clean covers known use cases. (`#8372 <https://github.com/pypa/pip/issues/8372>`_)
- Remove undocumented and deprecated option ``--always-unzip`` (`#8408 <https://github.com/pypa/pip/issues/8408>`_)

Features
--------

- Log debugging information about pip, in ``pip install --verbose``. (`#3166 <https://github.com/pypa/pip/issues/3166>`_)
- Refine error messages to avoid showing Python tracebacks when an HTTP error occurs. (`#5380 <https://github.com/pypa/pip/issues/5380>`_)
- Install wheel files directly instead of extracting them to a temp directory. (`#6030 <https://github.com/pypa/pip/issues/6030>`_)
- Add a beta version of pip's next-generation dependency resolver.

  Move pip's new resolver into beta, remove the
  ``--unstable-feature=resolver`` flag, and enable the
  ``--use-feature=2020-resolver`` flag. The new resolver is
  significantly stricter and more consistent when it receives
  incompatible instructions, and reduces support for certain kinds of
  :ref:`Constraints Files`, so some workarounds and workflows may
  break. More details about how to test and migrate, and how to report
  issues, at :ref:`Resolver changes 2020` . Maintainers are preparing to
  release pip 20.3, with the new resolver on by default, in October. (`#6536 <https://github.com/pypa/pip/issues/6536>`_)
- Introduce a new ResolutionImpossible error, raised when pip encounters un-satisfiable dependency conflicts (`#8546 <https://github.com/pypa/pip/issues/8546>`_, `#8377 <https://github.com/pypa/pip/issues/8377>`_)
- Add a subcommand ``debug`` to ``pip config`` to list available configuration sources and the key-value pairs defined in them. (`#6741 <https://github.com/pypa/pip/issues/6741>`_)
- Warn if index pages have unexpected content-type (`#6754 <https://github.com/pypa/pip/issues/6754>`_)
- Allow specifying ``--prefer-binary`` option in a requirements file (`#7693 <https://github.com/pypa/pip/issues/7693>`_)
- Generate PEP 376 REQUESTED metadata for user supplied requirements installed
  by pip. (`#7811 <https://github.com/pypa/pip/issues/7811>`_)
- Warn if package url is a vcs or an archive url with invalid scheme (`#8128 <https://github.com/pypa/pip/issues/8128>`_)
- Parallelize network operations in ``pip list``. (`#8504 <https://github.com/pypa/pip/issues/8504>`_)
- Allow the new resolver to obtain dependency information through wheels
  lazily downloaded using HTTP range requests.  To enable this feature,
  invoke ``pip`` with ``--use-feature=fast-deps``. (`#8588 <https://github.com/pypa/pip/issues/8588>`_)
- Support ``--use-feature`` in requirements files (`#8601 <https://github.com/pypa/pip/issues/8601>`_)

Bug Fixes
---------

- Use canonical package names while looking up already installed packages. (`#5021 <https://github.com/pypa/pip/issues/5021>`_)
- Fix normalizing path on Windows when installing package on another logical disk. (`#7625 <https://github.com/pypa/pip/issues/7625>`_)
- The VCS commands run by pip as subprocesses don't merge stdout and stderr anymore, improving the output parsing by subsequent commands. (`#7968 <https://github.com/pypa/pip/issues/7968>`_)
- Correctly treat non-ASCII entry point declarations in wheels so they can be
  installed on Windows. (`#8342 <https://github.com/pypa/pip/issues/8342>`_)
- Update author email in config and tests to reflect decommissioning of pypa-dev list. (`#8454 <https://github.com/pypa/pip/issues/8454>`_)
- Headers provided by wheels in .data directories are now correctly installed
  into the user-provided locations, such as ``--prefix``, instead of the virtual
  environment pip is running in. (`#8521 <https://github.com/pypa/pip/issues/8521>`_)

Vendored Libraries
------------------

- Vendored htmlib5 no longer imports deprecated xml.etree.cElementTree on Python 3.
- Upgrade appdirs to 1.4.4
- Upgrade certifi to 2020.6.20
- Upgrade distlib to 0.3.1
- Upgrade html5lib to 1.1
- Upgrade idna to 2.10
- Upgrade packaging to 20.4
- Upgrade requests to 2.24.0
- Upgrade six to 1.15.0
- Upgrade toml to 0.10.1
- Upgrade urllib3 to 1.25.9

Improved Documentation
----------------------

- Add ``--no-input`` option to pip docs (`#7688 <https://github.com/pypa/pip/issues/7688>`_)
- List of options supported in requirements file are extracted from source of truth,
  instead of being maintained manually. (`#7908 <https://github.com/pypa/pip/issues/7908>`_)
- Fix pip config docstring so that the subcommands render correctly in the docs (`#8072 <https://github.com/pypa/pip/issues/8072>`_)
- replace links to the old pypa-dev mailing list with https://mail.python.org/mailman3/lists/distutils-sig.python.org/ (`#8353 <https://github.com/pypa/pip/issues/8353>`_)
- Fix example for defining multiple values for options which support them (`#8373 <https://github.com/pypa/pip/issues/8373>`_)
- Add documentation for the ResolutionImpossible error that helps the user fix dependency conflicts (`#8459 <https://github.com/pypa/pip/issues/8459>`_)
- Add feature flags to docs (`#8512 <https://github.com/pypa/pip/issues/8512>`_)
- Document how to install package extras from git branch and source distributions. (`#8576 <https://github.com/pypa/pip/issues/8576>`_)


20.2b1 (2020-05-21)
===================

Bug Fixes
---------

- Correctly treat wheels containing non-ASCII file contents so they can be
  installed on Windows. (`#5712 <https://github.com/pypa/pip/issues/5712>`_)
- Prompt the user for password if the keyring backend doesn't return one (`#7998 <https://github.com/pypa/pip/issues/7998>`_)

Improved Documentation
----------------------

- Add GitHub issue template for reporting when the dependency resolver fails (`#8207 <https://github.com/pypa/pip/issues/8207>`_)

20.1.1 (2020-05-19)
===================

Deprecations and Removals
-------------------------

- Revert building of local directories in place, restoring the pre-20.1
  behaviour of copying to a temporary directory. (`#7555 <https://github.com/pypa/pip/issues/7555>`_)
- Drop parallelization from ``pip list --outdated``. (`#8167 <https://github.com/pypa/pip/issues/8167>`_)

Bug Fixes
---------

- Fix metadata permission issues when umask has the executable bit set. (`#8164 <https://github.com/pypa/pip/issues/8164>`_)
- Avoid unnecessary message about the wheel package not being installed
  when a wheel would not have been built. Additionally, clarify the message. (`#8178 <https://github.com/pypa/pip/issues/8178>`_)


20.1 (2020-04-28)
=================

Process
-------

- Document that pip 21.0 will drop support for Python 2.7.

Features
--------

- Add ``pip cache dir`` to show the cache directory. (`#7350 <https://github.com/pypa/pip/issues/7350>`_)

Bug Fixes
---------

- Abort pip cache commands early when cache is disabled. (`#8124 <https://github.com/pypa/pip/issues/8124>`_)
- Correctly set permissions on metadata files during wheel installation,
  to permit non-privileged users to read from system site-packages. (`#8139 <https://github.com/pypa/pip/issues/8139>`_)


20.1b1 (2020-04-21)
===================

Deprecations and Removals
-------------------------

- Remove emails from AUTHORS.txt to prevent usage for spamming, and only populate names in AUTHORS.txt at time of release (`#5979 <https://github.com/pypa/pip/issues/5979>`_)
- Remove deprecated ``--skip-requirements-regex`` option. (`#7297 <https://github.com/pypa/pip/issues/7297>`_)
- Building of local directories is now done in place, instead of a temporary
  location containing a copy of the directory tree. (`#7555 <https://github.com/pypa/pip/issues/7555>`_)
- Remove unused ``tests/scripts/test_all_pip.py`` test script and the ``tests/scripts`` folder. (`#7680 <https://github.com/pypa/pip/issues/7680>`_)

Features
--------

- pip now implements PEP 610, so ``pip freeze`` has better fidelity
  in presence of distributions installed from Direct URL requirements. (`#609 <https://github.com/pypa/pip/issues/609>`_)
- Add ``pip cache`` command for inspecting/managing pip's wheel cache. (`#6391 <https://github.com/pypa/pip/issues/6391>`_)
- Raise error if ``--user`` and ``--target`` are used together in ``pip install`` (`#7249 <https://github.com/pypa/pip/issues/7249>`_)
- Significantly improve performance when ``--find-links`` points to a very large HTML page. (`#7729 <https://github.com/pypa/pip/issues/7729>`_)
- Indicate when wheel building is skipped, due to lack of the ``wheel`` package. (`#7768 <https://github.com/pypa/pip/issues/7768>`_)
- Change default behaviour to always cache responses from trusted-host source. (`#7847 <https://github.com/pypa/pip/issues/7847>`_)
- An alpha version of a new resolver is available via ``--unstable-feature=resolver``. (`#988 <https://github.com/pypa/pip/issues/988>`_)

Bug Fixes
---------

- Correctly freeze a VCS editable package when it is nested inside another VCS repository. (`#3988 <https://github.com/pypa/pip/issues/3988>`_)
- Correctly handle ``%2F`` in URL parameters to avoid accidentally unescape them
  into ``/``. (`#6446 <https://github.com/pypa/pip/issues/6446>`_)
- Reject VCS URLs with an empty revision. (`#7402 <https://github.com/pypa/pip/issues/7402>`_)
- Warn when an invalid URL is passed with ``--index-url`` (`#7430 <https://github.com/pypa/pip/issues/7430>`_)
- Use better mechanism for handling temporary files, when recording metadata
  about installed files (RECORD) and the installer (INSTALLER). (`#7699 <https://github.com/pypa/pip/issues/7699>`_)
- Correctly detect global site-packages availability of virtual environments
  created by PyPA’s virtualenv>=20.0. (`#7718 <https://github.com/pypa/pip/issues/7718>`_)
- Remove current directory from ``sys.path`` when invoked as ``python -m pip <command>`` (`#7731 <https://github.com/pypa/pip/issues/7731>`_)
- Stop failing uninstallation, when trying to remove non-existent files. (`#7856 <https://github.com/pypa/pip/issues/7856>`_)
- Prevent an infinite recursion with ``pip wheel`` when ``$TMPDIR`` is within the source directory. (`#7872 <https://github.com/pypa/pip/issues/7872>`_)
- Significantly speedup ``pip list --outdated`` by parallelizing index interaction. (`#7962 <https://github.com/pypa/pip/issues/7962>`_)
- Improve Windows compatibility when detecting writability in folder. (`#8013 <https://github.com/pypa/pip/issues/8013>`_)

Vendored Libraries
------------------

- Update semi-supported debundling script to reflect that appdirs is vendored.
- Add ResolveLib as a vendored dependency.
- Upgrade certifi to 2020.04.05.1
- Upgrade contextlib2 to 0.6.0.post1
- Upgrade distro to 1.5.0.
- Upgrade idna to 2.9.
- Upgrade msgpack to 1.0.0.
- Upgrade packaging to 20.3.
- Upgrade pep517 to 0.8.2.
- Upgrade pyparsing to 2.4.7.
- Remove pytoml as a vendored dependency.
- Upgrade requests to 2.23.0.
- Add toml as a vendored dependency.
- Upgrade urllib3 to 1.25.8.

Improved Documentation
----------------------

- Emphasize that VCS URLs using git, git+git and git+http are insecure due to
  lack of authentication and encryption (`#1983 <https://github.com/pypa/pip/issues/1983>`_)
- Clarify the usage of --no-binary command. (`#3191 <https://github.com/pypa/pip/issues/3191>`_)
- Clarify the usage of freeze command in the example of Using pip in your program (`#7008 <https://github.com/pypa/pip/issues/7008>`_)
- Add a "Copyright" page. (`#7767 <https://github.com/pypa/pip/issues/7767>`_)
- Added example of defining multiple values for options which support them (`#7803 <https://github.com/pypa/pip/issues/7803>`_)


20.0.2 (2020-01-24)
===================

Bug Fixes
---------

- Fix a regression in generation of compatibility tags. (`#7626 <https://github.com/pypa/pip/issues/7626>`_)

Vendored Libraries
------------------

- Upgrade packaging to 20.1


20.0.1 (2020-01-21)
===================

Bug Fixes
---------

- Rename an internal module, to avoid ImportErrors due to improper uninstallation. (`#7621 <https://github.com/pypa/pip/issues/7621>`_)


20.0 (2020-01-21)
=================

Process
-------

- Switch to a dedicated CLI tool for vendoring dependencies.

Deprecations and Removals
-------------------------

- Remove wheel tag calculation from pip and use ``packaging.tags``. This
  should provide more tags ordered better than in prior releases. (`#6908 <https://github.com/pypa/pip/issues/6908>`_)
- Deprecate setup.py-based builds that do not generate an ``.egg-info`` directory. (`#6998 <https://github.com/pypa/pip/issues/6998>`_)
- The pip>=20 wheel cache is not retro-compatible with previous versions. Until
  pip 21.0, pip will continue to take advantage of existing legacy cache
  entries. (`#7296 <https://github.com/pypa/pip/issues/7296>`_)
- Deprecate undocumented ``--skip-requirements-regex`` option. (`#7297 <https://github.com/pypa/pip/issues/7297>`_)
- Deprecate passing install-location-related options via ``--install-option``. (`#7309 <https://github.com/pypa/pip/issues/7309>`_)
- Use literal "abi3" for wheel tag on CPython 3.x, to align with PEP 384
  which only defines it for this platform. (`#7327 <https://github.com/pypa/pip/issues/7327>`_)
- Remove interpreter-specific major version tag e.g. ``cp3-none-any``
  from consideration. This behavior was not documented strictly, and this
  tag in particular is `not useful <https://snarky.ca/the-challenges-in-designing-a-library-for-pep-425/>`_.
  Anyone with a use case can create an issue with pypa/packaging. (`#7355 <https://github.com/pypa/pip/issues/7355>`_)
- Wheel processing no longer permits wheels containing more than one top-level
  .dist-info directory. (`#7487 <https://github.com/pypa/pip/issues/7487>`_)
- Support for the ``git+git@`` form of VCS requirement is being deprecated and
  will be removed in pip 21.0. Switch to ``git+https://`` or
  ``git+ssh://``. ``git+git://`` also works but its use is discouraged as it is
  insecure. (`#7543 <https://github.com/pypa/pip/issues/7543>`_)

Features
--------

- Default to doing a user install (as if ``--user`` was passed) when the main
  site-packages directory is not writeable and user site-packages are enabled. (`#1668 <https://github.com/pypa/pip/issues/1668>`_)
- Warn if a path in PATH starts with tilde during ``pip install``. (`#6414 <https://github.com/pypa/pip/issues/6414>`_)
- Cache wheels built from Git requirements that are considered immutable,
  because they point to a commit hash. (`#6640 <https://github.com/pypa/pip/issues/6640>`_)
- Add option ``--no-python-version-warning`` to silence warnings
  related to deprecation of Python versions. (`#6673 <https://github.com/pypa/pip/issues/6673>`_)
- Cache wheels that ``pip wheel`` built locally, matching what
  ``pip install`` does. This particularly helps performance in workflows where
  ``pip wheel`` is used for `building before installing
  <https://pip.pypa.io/en/stable/user_guide/#installing-from-local-packages>`_.
  Users desiring the original behavior can use ``pip wheel --no-cache-dir``. (`#6852 <https://github.com/pypa/pip/issues/6852>`_)
- Display CA information in ``pip debug``. (`#7146 <https://github.com/pypa/pip/issues/7146>`_)
- Show only the filename (instead of full URL), when downloading from PyPI. (`#7225 <https://github.com/pypa/pip/issues/7225>`_)
- Suggest a more robust command to upgrade pip itself to avoid confusion when the
  current pip command is not available as ``pip``. (`#7376 <https://github.com/pypa/pip/issues/7376>`_)
- Define all old pip console script entrypoints to prevent import issues in
  stale wrapper scripts. (`#7498 <https://github.com/pypa/pip/issues/7498>`_)
- The build step of ``pip wheel`` now builds all wheels to a cache first,
  then copies them to the wheel directory all at once.
  Before, it built them to a temporary directory and moved
  them to the wheel directory one by one. (`#7517 <https://github.com/pypa/pip/issues/7517>`_)
- Expand ``~`` prefix to user directory in path options, configs, and
  environment variables. Values that may be either URL or path are not
  currently supported, to avoid ambiguity:

  * ``--find-links``
  * ``--constraint``, ``-c``
  * ``--requirement``, ``-r``
  * ``--editable``, ``-e`` (`#980 <https://github.com/pypa/pip/issues/980>`_)

Bug Fixes
---------

- Correctly handle system site-packages, in virtual environments created with venv (PEP 405). (`#5702 <https://github.com/pypa/pip/issues/5702>`_, `#7155 <https://github.com/pypa/pip/issues/7155>`_)
- Fix case sensitive comparison of pip freeze when used with -r option. (`#5716 <https://github.com/pypa/pip/issues/5716>`_)
- Enforce PEP 508 requirement format in ``pyproject.toml``
  ``build-system.requires``. (`#6410 <https://github.com/pypa/pip/issues/6410>`_)
- Make ``ensure_dir()`` also ignore ``ENOTEMPTY`` as seen on Windows. (`#6426 <https://github.com/pypa/pip/issues/6426>`_)
- Fix building packages which specify ``backend-path`` in pyproject.toml. (`#6599 <https://github.com/pypa/pip/issues/6599>`_)
- Do not attempt to run ``setup.py clean`` after a ``pep517`` build error,
  since a ``setup.py`` may not exist in that case. (`#6642 <https://github.com/pypa/pip/issues/6642>`_)
- Fix passwords being visible in the index-url in
  "Downloading <url>" message. (`#6783 <https://github.com/pypa/pip/issues/6783>`_)
- Change method from shutil.remove to shutil.rmtree in noxfile.py. (`#7191 <https://github.com/pypa/pip/issues/7191>`_)
- Skip running tests which require subversion, when svn isn't installed (`#7193 <https://github.com/pypa/pip/issues/7193>`_)
- Fix not sending client certificates when using ``--trusted-host``. (`#7207 <https://github.com/pypa/pip/issues/7207>`_)
- Make sure ``pip wheel`` never outputs pure python wheels with a
  python implementation tag. Better fix/workaround for
  `#3025 <https://github.com/pypa/pip/issues/3025>`_ by
  using a per-implementation wheel cache instead of caching pure python
  wheels with an implementation tag in their name. (`#7296 <https://github.com/pypa/pip/issues/7296>`_)
- Include ``subdirectory`` URL fragments in cache keys. (`#7333 <https://github.com/pypa/pip/issues/7333>`_)
- Fix typo in warning message when any of ``--build-option``, ``--global-option``
  and ``--install-option`` is used in requirements.txt (`#7340 <https://github.com/pypa/pip/issues/7340>`_)
- Fix the logging of cached HTTP response shown as downloading. (`#7393 <https://github.com/pypa/pip/issues/7393>`_)
- Effectively disable the wheel cache when it is not writable, as is the
  case with the http cache. (`#7488 <https://github.com/pypa/pip/issues/7488>`_)
- Correctly handle relative cache directory provided via --cache-dir. (`#7541 <https://github.com/pypa/pip/issues/7541>`_)

Vendored Libraries
------------------

- Upgrade CacheControl to 0.12.5
- Upgrade certifi to 2019.9.11
- Upgrade colorama to 0.4.1
- Upgrade distlib to 0.2.9.post0
- Upgrade ipaddress to 1.0.22
- Update packaging to 20.0.
- Upgrade pkg_resources (via setuptools) to 44.0.0
- Upgrade pyparsing to 2.4.2
- Upgrade six to 1.12.0
- Upgrade urllib3 to 1.25.6

Improved Documentation
----------------------

- Document that "coding: utf-8" is supported in requirements.txt (`#7182 <https://github.com/pypa/pip/issues/7182>`_)
- Explain how to get pip's source code in `Getting Started <https://pip.pypa.io/en/stable/development/getting-started/>`_ (`#7197 <https://github.com/pypa/pip/issues/7197>`_)
- Describe how basic authentication credentials in URLs work. (`#7201 <https://github.com/pypa/pip/issues/7201>`_)
- Add more clear installation instructions (`#7222 <https://github.com/pypa/pip/issues/7222>`_)
- Fix documentation links for index options (`#7347 <https://github.com/pypa/pip/issues/7347>`_)
- Better document the requirements file format (`#7385 <https://github.com/pypa/pip/issues/7385>`_)


19.3.1 (2019-10-17)
===================

Features
--------

- Document Python 3.8 support. (`#7219 <https://github.com/pypa/pip/issues/7219>`_)

Bug Fixes
---------

- Fix bug that prevented installation of PEP 517 packages without ``setup.py``. (`#6606 <https://github.com/pypa/pip/issues/6606>`_)


19.3 (2019-10-14)
=================

Deprecations and Removals
-------------------------

- Remove undocumented support for un-prefixed URL requirements pointing
  to SVN repositories. Users relying on this can get the original behavior
  by prefixing their URL with ``svn+`` (which is backwards-compatible). (`#7037 <https://github.com/pypa/pip/issues/7037>`_)
- Remove the deprecated ``--venv`` option from ``pip config``. (`#7163 <https://github.com/pypa/pip/issues/7163>`_)

Features
--------

- Print a better error message when ``--no-binary`` or ``--only-binary`` is given
  an argument starting with ``-``. (`#3191 <https://github.com/pypa/pip/issues/3191>`_)
- Make ``pip show`` warn about packages not found. (`#6858 <https://github.com/pypa/pip/issues/6858>`_)
- Support including a port number in ``--trusted-host`` for both HTTP and HTTPS. (`#6886 <https://github.com/pypa/pip/issues/6886>`_)
- Redact single-part login credentials from URLs in log messages. (`#6891 <https://github.com/pypa/pip/issues/6891>`_)
- Implement manylinux2014 platform tag support.  manylinux2014 is the successor
  to manylinux2010.  It allows carefully compiled binary wheels to be installed
  on compatible Linux platforms.  The manylinux2014 platform tag definition can
  be found in `PEP599 <https://www.python.org/dev/peps/pep-0599/>`_. (`#7102 <https://github.com/pypa/pip/issues/7102>`_)

Bug Fixes
---------

- Abort installation if any archive contains a file which would be placed
  outside the extraction location. (`#3907 <https://github.com/pypa/pip/issues/3907>`_)
- pip's CLI completion code no longer prints a Traceback if it is interrupted. (`#3942 <https://github.com/pypa/pip/issues/3942>`_)
- Correct inconsistency related to the ``hg+file`` scheme. (`#4358 <https://github.com/pypa/pip/issues/4358>`_)
- Fix ``rmtree_errorhandler`` to skip non-existing directories. (`#4910 <https://github.com/pypa/pip/issues/4910>`_)
- Ignore errors copying socket files for local source installs (in Python 3). (`#5306 <https://github.com/pypa/pip/issues/5306>`_)
- Fix requirement line parser to correctly handle PEP 440 requirements with a URL
  pointing to an archive file. (`#6202 <https://github.com/pypa/pip/issues/6202>`_)
- The ``pip-wheel-metadata`` directory does not need to persist between invocations of pip, use a temporary directory instead of the current ``setup.py`` directory. (`#6213 <https://github.com/pypa/pip/issues/6213>`_)
- Fix ``--trusted-host`` processing under HTTPS to trust any port number used
  with the host. (`#6705 <https://github.com/pypa/pip/issues/6705>`_)
- Switch to new ``distlib`` wheel script template. This should be functionally
  equivalent for end users. (`#6763 <https://github.com/pypa/pip/issues/6763>`_)
- Skip copying .tox and .nox directories to temporary build directories (`#6770 <https://github.com/pypa/pip/issues/6770>`_)
- Fix handling of tokens (single part credentials) in URLs. (`#6795 <https://github.com/pypa/pip/issues/6795>`_)
- Fix a regression that caused ``~`` expansion not to occur in ``--find-links``
  paths. (`#6804 <https://github.com/pypa/pip/issues/6804>`_)
- Fix bypassed pip upgrade warning on Windows. (`#6841 <https://github.com/pypa/pip/issues/6841>`_)
- Fix 'm' flag erroneously being appended to ABI tag in Python 3.8 on platforms that do not provide SOABI (`#6885 <https://github.com/pypa/pip/issues/6885>`_)
- Hide security-sensitive strings like passwords in log messages related to
  version control system (aka VCS) command invocations. (`#6890 <https://github.com/pypa/pip/issues/6890>`_)
- Correctly uninstall symlinks that were installed in a virtualenv,
  by tools such as ``flit install --symlink``. (`#6892 <https://github.com/pypa/pip/issues/6892>`_)
- Don't fail installation using pip.exe on Windows when pip wouldn't be upgraded. (`#6924 <https://github.com/pypa/pip/issues/6924>`_)
- Use canonical distribution names when computing ``Required-By`` in ``pip show``. (`#6947 <https://github.com/pypa/pip/issues/6947>`_)
- Don't use hardlinks for locking selfcheck state file. (`#6954 <https://github.com/pypa/pip/issues/6954>`_)
- Ignore "require_virtualenv" in ``pip config`` (`#6991 <https://github.com/pypa/pip/issues/6991>`_)
- Fix ``pip freeze`` not showing correct entry for mercurial packages that use subdirectories. (`#7071 <https://github.com/pypa/pip/issues/7071>`_)
- Fix a crash when ``sys.stdin`` is set to ``None``, such as on AWS Lambda. (`#7118 <https://github.com/pypa/pip/issues/7118>`_, `#7119 <https://github.com/pypa/pip/issues/7119>`_)

Vendored Libraries
------------------

- Upgrade certifi to 2019.9.11
- Add contextlib2 0.6.0 as a vendored dependency.
- Remove Lockfile as a vendored dependency.
- Upgrade msgpack to 0.6.2
- Upgrade packaging to 19.2
- Upgrade pep517 to 0.7.0
- Upgrade pyparsing to 2.4.2
- Upgrade pytoml to 0.1.21
- Upgrade setuptools to 41.4.0
- Upgrade urllib3 to 1.25.6

Improved Documentation
----------------------

- Document caveats for UNC paths in uninstall and add .pth unit tests. (`#6516 <https://github.com/pypa/pip/issues/6516>`_)
- Add architectural overview documentation. (`#6637 <https://github.com/pypa/pip/issues/6637>`_)
- Document that ``--ignore-installed`` is dangerous. (`#6794 <https://github.com/pypa/pip/issues/6794>`_)


19.2.3 (2019-08-25)
===================

Bug Fixes
---------

- Fix 'm' flag erroneously being appended to ABI tag in Python 3.8 on platforms that do not provide SOABI (`#6885 <https://github.com/pypa/pip/issues/6885>`_)


19.2.2 (2019-08-11)
===================

Bug Fixes
---------

- Fix handling of tokens (single part credentials) in URLs. (`#6795 <https://github.com/pypa/pip/issues/6795>`_)
- Fix a regression that caused ``~`` expansion not to occur in ``--find-links``
  paths. (`#6804 <https://github.com/pypa/pip/issues/6804>`_)


19.2.1 (2019-07-23)
===================

Bug Fixes
---------

- Fix a ``NoneType`` ``AttributeError`` when evaluating hashes and no hashes
  are provided. (`#6772 <https://github.com/pypa/pip/issues/6772>`_)


19.2 (2019-07-22)
=================

Deprecations and Removals
-------------------------

- Drop support for EOL Python 3.4. (`#6685 <https://github.com/pypa/pip/issues/6685>`_)
- Improve deprecation messages to include the version in which the functionality will be removed. (`#6549 <https://github.com/pypa/pip/issues/6549>`_)

Features
--------

- Credentials will now be loaded using `keyring` when installed. (`#5948 <https://github.com/pypa/pip/issues/5948>`_)
- Fully support using ``--trusted-host`` inside requirements files. (`#3799 <https://github.com/pypa/pip/issues/3799>`_)
- Update timestamps in pip's ``--log`` file to include milliseconds. (`#6587 <https://github.com/pypa/pip/issues/6587>`_)
- Respect whether a file has been marked as "yanked" from a simple repository
  (see `PEP 592 <https://www.python.org/dev/peps/pep-0592/>`__ for details). (`#6633 <https://github.com/pypa/pip/issues/6633>`_)
- When choosing candidates to install, prefer candidates with a hash matching
  one of the user-provided hashes. (`#5874 <https://github.com/pypa/pip/issues/5874>`_)
- Improve the error message when ``METADATA`` or ``PKG-INFO`` is None when
  accessing metadata. (`#5082 <https://github.com/pypa/pip/issues/5082>`_)
- Add a new command ``pip debug`` that can display e.g. the list of compatible
  tags for the current Python. (`#6638 <https://github.com/pypa/pip/issues/6638>`_)
- Display hint on installing with --pre when search results include pre-release versions. (`#5169 <https://github.com/pypa/pip/issues/5169>`_)
- Report to Warehouse that pip is running under CI if the ``PIP_IS_CI`` environment variable is set. (`#5499 <https://github.com/pypa/pip/issues/5499>`_)
- Allow ``--python-version`` to be passed as a dotted version string (e.g.
  ``3.7`` or ``3.7.3``). (`#6585 <https://github.com/pypa/pip/issues/6585>`_)
- Log the final filename and SHA256 of a ``.whl`` file when done building a
  wheel. (`#5908 <https://github.com/pypa/pip/issues/5908>`_)
- Include the wheel's tags in the log message explanation when a candidate
  wheel link is found incompatible. (`#6121 <https://github.com/pypa/pip/issues/6121>`_)
- Add a ``--path`` argument to ``pip freeze`` to support ``--target``
  installations. (`#6404 <https://github.com/pypa/pip/issues/6404>`_)
- Add a ``--path`` argument to ``pip list`` to support ``--target``
  installations. (`#6551 <https://github.com/pypa/pip/issues/6551>`_)

Bug Fixes
---------

- Set ``sys.argv[0]`` to the underlying ``setup.py`` when invoking ``setup.py``
  via the setuptools shim so setuptools doesn't think the path is ``-c``. (`#1890 <https://github.com/pypa/pip/issues/1890>`_)
- Update ``pip download`` to respect the given ``--python-version`` when checking
  ``"Requires-Python"``. (`#5369 <https://github.com/pypa/pip/issues/5369>`_)
- Respect ``--global-option`` and ``--install-option`` when installing from
  a version control url (e.g. ``git``). (`#5518 <https://github.com/pypa/pip/issues/5518>`_)
- Make the "ascii" progress bar really be "ascii" and not Unicode. (`#5671 <https://github.com/pypa/pip/issues/5671>`_)
- Fail elegantly when trying to set an incorrectly formatted key in config. (`#5963 <https://github.com/pypa/pip/issues/5963>`_)
- Prevent DistutilsOptionError when prefix is indicated in the global environment and `--target` is used. (`#6008 <https://github.com/pypa/pip/issues/6008>`_)
- Fix ``pip install`` to respect ``--ignore-requires-python`` when evaluating
  links. (`#6371 <https://github.com/pypa/pip/issues/6371>`_)
- Fix a debug log message when freezing an editable, non-version controlled
  requirement. (`#6383 <https://github.com/pypa/pip/issues/6383>`_)
- Extend to Subversion 1.8+ the behavior of calling Subversion in
  interactive mode when pip is run interactively. (`#6386 <https://github.com/pypa/pip/issues/6386>`_)
- Prevent ``pip install <url>`` from permitting directory traversal if e.g.
  a malicious server sends a ``Content-Disposition`` header with a filename
  containing ``../`` or ``..\\``. (`#6413 <https://github.com/pypa/pip/issues/6413>`_)
- Hide passwords in output when using ``--find-links``. (`#6489 <https://github.com/pypa/pip/issues/6489>`_)
- Include more details in the log message if ``pip freeze`` can't generate a
  requirement string for a particular distribution. (`#6513 <https://github.com/pypa/pip/issues/6513>`_)
- Add the line number and file location to the error message when reading an
  invalid requirements file in certain situations. (`#6527 <https://github.com/pypa/pip/issues/6527>`_)
- Prefer ``os.confstr`` to ``ctypes`` when extracting glibc version info. (`#6543 <https://github.com/pypa/pip/issues/6543>`_, `#6675 <https://github.com/pypa/pip/issues/6675>`_)
- Improve error message printed when an invalid editable requirement is provided. (`#6648 <https://github.com/pypa/pip/issues/6648>`_)
- Improve error message formatting when a command errors out in a subprocess. (`#6651 <https://github.com/pypa/pip/issues/6651>`_)

Vendored Libraries
------------------

- Upgrade certifi to 2019.6.16
- Upgrade distlib to 0.2.9.post0
- Upgrade msgpack to 0.6.1
- Upgrade requests to 2.22.0
- Upgrade urllib3 to 1.25.3
- Patch vendored html5lib, to prefer using `collections.abc` where possible.

Improved Documentation
----------------------

- Document how Python 2.7 support will be maintained. (`#6726 <https://github.com/pypa/pip/issues/6726>`_)
- Upgrade Sphinx version used to build documentation. (`#6471 <https://github.com/pypa/pip/issues/6471>`_)
- Fix generation of subcommand manpages. (`#6724 <https://github.com/pypa/pip/issues/6724>`_)
- Mention that pip can install from git refs. (`#6512 <https://github.com/pypa/pip/issues/6512>`_)
- Replace a failing example of pip installs with extras with a working one. (`#4733 <https://github.com/pypa/pip/issues/4733>`_)

19.1.1 (2019-05-06)
===================

Features
--------

- Restore ``pyproject.toml`` handling to how it was with pip 19.0.3 to prevent
  the need to add ``--no-use-pep517`` when installing in editable mode. (`#6434 <https://github.com/pypa/pip/issues/6434>`_)

Bug Fixes
---------

- Fix a regression that caused `@` to be quoted in pypiserver links.
  This interfered with parsing the revision string from VCS urls. (`#6440 <https://github.com/pypa/pip/issues/6440>`_)


19.1 (2019-04-23)
=================

Features
--------

- Configuration files may now also be stored under ``sys.prefix`` (`#5060 <https://github.com/pypa/pip/issues/5060>`_)
- Avoid creating an unnecessary local clone of a Bazaar branch when exporting. (`#5443 <https://github.com/pypa/pip/issues/5443>`_)
- Include in pip's User-Agent string whether it looks like pip is running
  under CI. (`#5499 <https://github.com/pypa/pip/issues/5499>`_)
- A custom (JSON-encoded) string can now be added to pip's User-Agent
  using the ``PIP_USER_AGENT_USER_DATA`` environment variable. (`#5549 <https://github.com/pypa/pip/issues/5549>`_)
- For consistency, passing ``--no-cache-dir`` no longer affects whether wheels
  will be built.  In this case, a temporary directory is used. (`#5749 <https://github.com/pypa/pip/issues/5749>`_)
- Command arguments in ``subprocess`` log messages are now quoted using
  ``shlex.quote()``. (`#6290 <https://github.com/pypa/pip/issues/6290>`_)
- Prefix warning and error messages in log output with `WARNING` and `ERROR`. (`#6298 <https://github.com/pypa/pip/issues/6298>`_)
- Using ``--build-options`` in a PEP 517 build now fails with an error,
  rather than silently ignoring the option. (`#6305 <https://github.com/pypa/pip/issues/6305>`_)
- Error out with an informative message if one tries to install a
  ``pyproject.toml``-style (PEP 517) source tree using ``--editable`` mode. (`#6314 <https://github.com/pypa/pip/issues/6314>`_)
- When downloading a package, the ETA and average speed now only update once per second for better legibility. (`#6319 <https://github.com/pypa/pip/issues/6319>`_)

Bug Fixes
---------

- The stdout and stderr from VCS commands run by pip as subprocesses (e.g.
  ``git``, ``hg``, etc.) no longer pollute pip's stdout. (`#1219 <https://github.com/pypa/pip/issues/1219>`_)
- Fix handling of requests exceptions when dependencies are debundled. (`#4195 <https://github.com/pypa/pip/issues/4195>`_)
- Make pip's self version check avoid recommending upgrades to prereleases if the currently-installed version is stable. (`#5175 <https://github.com/pypa/pip/issues/5175>`_)
- Fixed crash when installing a requirement from a URL that comes from a dependency without a URL. (`#5889 <https://github.com/pypa/pip/issues/5889>`_)
- Improve handling of file URIs: correctly handle `file://localhost/...` and don't try to use UNC paths on Unix. (`#5892 <https://github.com/pypa/pip/issues/5892>`_)
- Fix ``utils.encoding.auto_decode()`` ``LookupError`` with invalid encodings.
  ``utils.encoding.auto_decode()`` was broken when decoding Big Endian BOM
  byte-strings on Little Endian or vice versa. (`#6054 <https://github.com/pypa/pip/issues/6054>`_)
- Fix incorrect URL quoting of IPv6 addresses. (`#6285 <https://github.com/pypa/pip/issues/6285>`_)
- Redact the password from the extra index URL when using ``pip -v``. (`#6295 <https://github.com/pypa/pip/issues/6295>`_)
- The spinner no longer displays a completion message after subprocess calls
  not needing a spinner. It also no longer incorrectly reports an error after
  certain subprocess calls to Git that succeeded. (`#6312 <https://github.com/pypa/pip/issues/6312>`_)
- Fix the handling of editable mode during installs when ``pyproject.toml`` is
  present but PEP 517 doesn't require the source tree to be treated as
  ``pyproject.toml``-style. (`#6370 <https://github.com/pypa/pip/issues/6370>`_)
- Fix ``NameError`` when handling an invalid requirement. (`#6419 <https://github.com/pypa/pip/issues/6419>`_)

Vendored Libraries
------------------

- Updated certifi to 2019.3.9
- Updated distro to 1.4.0
- Update progress to 1.5
- Updated pyparsing to 2.4.0
- Updated pkg_resources to 41.0.1 (via setuptools)

Improved Documentation
----------------------

- Make dashes render correctly when displaying long options like
  ``--find-links`` in the text. (`#6422 <https://github.com/pypa/pip/issues/6422>`_)


19.0.3 (2019-02-20)
===================

Bug Fixes
---------

- Fix an ``IndexError`` crash when a legacy build of a wheel fails. (`#6252 <https://github.com/pypa/pip/issues/6252>`_)
- Fix a regression introduced in 19.0.2 where the filename in a RECORD file
  of an installed file would not be updated when installing a wheel. (`#6266 <https://github.com/pypa/pip/issues/6266>`_)


19.0.2 (2019-02-09)
===================

Bug Fixes
---------

- Fix a crash where PEP 517-based builds using ``--no-cache-dir`` would fail in
  some circumstances with an ``AssertionError`` due to not finalizing a build
  directory internally. (`#6197 <https://github.com/pypa/pip/issues/6197>`_)
- Provide a better error message if attempting an editable install of a
  directory with a ``pyproject.toml`` but no ``setup.py``. (`#6170 <https://github.com/pypa/pip/issues/6170>`_)
- The implicit default backend used for projects that provide a ``pyproject.toml``
  file without explicitly specifying ``build-backend`` now behaves more like direct
  execution of ``setup.py``, and hence should restore compatibility with projects
  that were unable to be installed with ``pip`` 19.0. This raised the minimum
  required version of ``setuptools`` for such builds to 40.8.0. (`#6163 <https://github.com/pypa/pip/issues/6163>`_)
- Allow ``RECORD`` lines with more than three elements, and display a warning. (`#6165 <https://github.com/pypa/pip/issues/6165>`_)
- ``AdjacentTempDirectory`` fails on unwritable directory instead of locking up the uninstall command. (`#6169 <https://github.com/pypa/pip/issues/6169>`_)
- Make failed uninstalls roll back more reliably and better at avoiding naming conflicts. (`#6194 <https://github.com/pypa/pip/issues/6194>`_)
- Ensure the correct wheel file is copied when building PEP 517 distribution is built. (`#6196 <https://github.com/pypa/pip/issues/6196>`_)
- The Python 2 end of life warning now only shows on CPython, which is the
  implementation that has announced end of life plans. (`#6207 <https://github.com/pypa/pip/issues/6207>`_)

Improved Documentation
----------------------

- Re-write README and documentation index (`#5815 <https://github.com/pypa/pip/issues/5815>`_)


19.0.1 (2019-01-23)
===================

Bug Fixes
---------

- Fix a crash when using --no-cache-dir with PEP 517 distributions (`#6158 <https://github.com/pypa/pip/issues/6158>`_, `#6171 <https://github.com/pypa/pip/issues/6171>`_)


19.0 (2019-01-22)
=================

Deprecations and Removals
-------------------------

- Deprecate support for Python 3.4 (`#6106 <https://github.com/pypa/pip/issues/6106>`_)
- Start printing a warning for Python 2.7 to warn of impending Python 2.7 End-of-life and
  prompt users to start migrating to Python 3. (`#6148 <https://github.com/pypa/pip/issues/6148>`_)
- Remove the deprecated ``--process-dependency-links`` option. (`#6060 <https://github.com/pypa/pip/issues/6060>`_)
- Remove the deprecated SVN editable detection based on dependency links
  during freeze. (`#5866 <https://github.com/pypa/pip/issues/5866>`_)

Features
--------

- Implement PEP 517 (allow projects to specify a build backend via pyproject.toml). (`#5743 <https://github.com/pypa/pip/issues/5743>`_)
- Implement manylinux2010 platform tag support.  manylinux2010 is the successor
  to manylinux1.  It allows carefully compiled binary wheels to be installed
  on compatible Linux platforms. (`#5008 <https://github.com/pypa/pip/issues/5008>`_)
- Improve build isolation: handle ``.pth`` files, so namespace packages are correctly supported under Python 3.2 and earlier. (`#5656 <https://github.com/pypa/pip/issues/5656>`_)
- Include the package name in a freeze warning if the package is not installed. (`#5943 <https://github.com/pypa/pip/issues/5943>`_)
- Warn when dropping an ``--[extra-]index-url`` value that points to an existing local directory. (`#5827 <https://github.com/pypa/pip/issues/5827>`_)
- Prefix pip's ``--log`` file lines with their timestamp. (`#6141 <https://github.com/pypa/pip/issues/6141>`_)

Bug Fixes
---------

- Avoid creating excessively long temporary paths when uninstalling packages. (`#3055 <https://github.com/pypa/pip/issues/3055>`_)
- Redact the password from the URL in various log messages. (`#4746 <https://github.com/pypa/pip/issues/4746>`_, `#6124 <https://github.com/pypa/pip/issues/6124>`_)
- Avoid creating excessively long temporary paths when uninstalling packages. (`#3055 <https://github.com/pypa/pip/issues/3055>`_)
- Avoid printing a stack trace when given an invalid requirement. (`#5147 <https://github.com/pypa/pip/issues/5147>`_)
- Present 401 warning if username/password do not work for URL (`#4833 <https://github.com/pypa/pip/issues/4833>`_)
- Handle ``requests.exceptions.RetryError`` raised in ``PackageFinder`` that was causing pip to fail silently when some indexes were unreachable. (`#5270 <https://github.com/pypa/pip/issues/5270>`_, `#5483 <https://github.com/pypa/pip/issues/5483>`_)
- Handle a broken stdout pipe more gracefully (e.g. when running ``pip list | head``). (`#4170 <https://github.com/pypa/pip/issues/4170>`_)
- Fix crash from setting ``PIP_NO_CACHE_DIR=yes``. (`#5385 <https://github.com/pypa/pip/issues/5385>`_)
- Fix crash from unparsable requirements when checking installed packages. (`#5839 <https://github.com/pypa/pip/issues/5839>`_)
- Fix content type detection if a directory named like an archive is used as a package source. (`#5838 <https://github.com/pypa/pip/issues/5838>`_)
- Fix listing of outdated packages that are not dependencies of installed packages in ``pip list --outdated --not-required`` (`#5737 <https://github.com/pypa/pip/issues/5737>`_)
- Fix sorting ``TypeError`` in ``move_wheel_files()`` when installing some packages. (`#5868 <https://github.com/pypa/pip/issues/5868>`_)
- Fix support for invoking pip using ``python src/pip ...``. (`#5841 <https://github.com/pypa/pip/issues/5841>`_)
- Greatly reduce memory usage when installing wheels containing large files. (`#5848 <https://github.com/pypa/pip/issues/5848>`_)
- Editable non-VCS installs now freeze as editable. (`#5031 <https://github.com/pypa/pip/issues/5031>`_)
- Editable Git installs without a remote now freeze as editable. (`#4759 <https://github.com/pypa/pip/issues/4759>`_)
- Canonicalize sdist file names so they can be matched to a canonicalized package name passed to ``pip install``. (`#5870 <https://github.com/pypa/pip/issues/5870>`_)
- Properly decode special characters in SVN URL credentials. (`#5968 <https://github.com/pypa/pip/issues/5968>`_)
- Make ``PIP_NO_CACHE_DIR`` disable the cache also for truthy values like ``"true"``, ``"yes"``, ``"1"``, etc. (`#5735 <https://github.com/pypa/pip/issues/5735>`_)

Vendored Libraries
------------------

- Include license text of vendored 3rd party libraries. (`#5213 <https://github.com/pypa/pip/issues/5213>`_)
- Update certifi to 2018.11.29
- Update colorama to 0.4.1
- Update distlib to 0.2.8
- Update idna to 2.8
- Update packaging to 19.0
- Update pep517 to 0.5.0
- Update pkg_resources to 40.6.3 (via setuptools)
- Update pyparsing to 2.3.1
- Update pytoml to 0.1.20
- Update requests to 2.21.0
- Update six to 1.12.0
- Update urllib3 to 1.24.1

Improved Documentation
----------------------

- Include the Vendoring Policy in the documentation. (`#5958 <https://github.com/pypa/pip/issues/5958>`_)
- Add instructions for running pip from source to Development documentation. (`#5949 <https://github.com/pypa/pip/issues/5949>`_)
- Remove references to removed ``#egg=<name>-<version>`` functionality (`#5888 <https://github.com/pypa/pip/issues/5888>`_)
- Fix omission of command name in HTML usage documentation (`#5984 <https://github.com/pypa/pip/issues/5984>`_)


18.1 (2018-10-05)
=================

Features
--------

- Allow PEP 508 URL requirements to be used as dependencies.

  As a security measure, pip will raise an exception when installing packages from
  PyPI if those packages depend on packages not also hosted on PyPI.
  In the future, PyPI will block uploading packages with such external URL dependencies directly. (`#4187 <https://github.com/pypa/pip/issues/4187>`_)
- Allows dist options (--abi, --python-version, --platform, --implementation) when installing with --target (`#5355 <https://github.com/pypa/pip/issues/5355>`_)
- Support passing ``svn+ssh`` URLs with a username to ``pip install -e``. (`#5375 <https://github.com/pypa/pip/issues/5375>`_)
- pip now ensures that the RECORD file is sorted when installing from a wheel file. (`#5525 <https://github.com/pypa/pip/issues/5525>`_)
- Add support for Python 3.7. (`#5561 <https://github.com/pypa/pip/issues/5561>`_)
- Malformed configuration files now show helpful error messages, instead of tracebacks. (`#5798 <https://github.com/pypa/pip/issues/5798>`_)

Bug Fixes
---------

- Checkout the correct branch when doing an editable Git install. (`#2037 <https://github.com/pypa/pip/issues/2037>`_)
- Run self-version-check only on commands that may access the index, instead of
  trying on every run and failing to do so due to missing options. (`#5433 <https://github.com/pypa/pip/issues/5433>`_)
- Allow a Git ref to be installed over an existing installation. (`#5624 <https://github.com/pypa/pip/issues/5624>`_)
- Show a better error message when a configuration option has an invalid value. (`#5644 <https://github.com/pypa/pip/issues/5644>`_)
- Always revalidate cached simple API pages instead of blindly caching them for up to 10
  minutes. (`#5670 <https://github.com/pypa/pip/issues/5670>`_)
- Avoid caching self-version-check information when cache is disabled. (`#5679 <https://github.com/pypa/pip/issues/5679>`_)
- Avoid traceback printing on autocomplete after flags in the CLI. (`#5751 <https://github.com/pypa/pip/issues/5751>`_)
- Fix incorrect parsing of egg names if pip needs to guess the package name. (`#5819 <https://github.com/pypa/pip/issues/5819>`_)

Vendored Libraries
------------------

- Upgrade certifi to 2018.8.24
- Upgrade packaging to 18.0
- Upgrade pyparsing to 2.2.1
- Add pep517 version 0.2
- Upgrade pytoml to 0.1.19
- Upgrade pkg_resources to 40.4.3 (via setuptools)

Improved Documentation
----------------------

- Fix "Requirements Files" reference in User Guide (`#user_guide_fix_requirements_file_ref <https://github.com/pypa/pip/issues/user_guide_fix_requirements_file_ref>`_)


18.0 (2018-07-22)
=================

Process
-------

- Switch to a Calendar based versioning scheme.
- Formally document our deprecation process as a minimum of 6 months of deprecation
  warnings.
- Adopt and document NEWS fragment writing style.
- Switch to releasing a new, non-bug fix version of pip every 3 months.

Deprecations and Removals
-------------------------

- Remove the legacy format from pip list. (#3651, #3654)
- Dropped support for Python 3.3. (#3796)
- Remove support for cleaning up #egg fragment postfixes. (#4174)
- Remove the shim for the old get-pip.py location. (#5520)

  For the past 2 years, it's only been redirecting users to use the newer
  https://bootstrap.pypa.io/get-pip.py location.

Features
--------

- Introduce a new --prefer-binary flag, to prefer older wheels over newer source packages. (#3785)
- Improve autocompletion function on file name completion after options
  which have ``<file>``, ``<dir>`` or ``<path>`` as metavar. (#4842, #5125)
- Add support for installing PEP 518 build dependencies from source. (#5229)
- Improve status message when upgrade is skipped due to only-if-needed strategy. (#5319)

Bug Fixes
---------

- Update pip's self-check logic to not use a virtualenv specific file and honor cache-dir. (#3905)
- Remove compiled pyo files for wheel packages. (#4471)
- Speed up printing of newly installed package versions. (#5127)
- Restrict install time dependency warnings to directly-dependant packages. (#5196, #5457)

  Warning about the entire package set has resulted in users getting confused as
  to why pip is printing these warnings.
- Improve handling of PEP 518 build requirements: support environment markers and extras. (#5230, #5265)
- Remove username/password from log message when using index with basic auth. (#5249)
- Remove trailing os.sep from PATH directories to avoid false negatives. (#5293)
- Fix "pip wheel pip" being blocked by the "don't use pip to modify itself" check. (#5311, #5312)
- Disable pip's version check (and upgrade message) when installed by a different package manager. (#5346)

  This works better with Linux distributions where pip's upgrade message may
  result in users running pip in a manner that modifies files that should be
  managed by the OS's package manager.
- Check for file existence and unlink first when clobbering existing files during a wheel install. (#5366)
- Improve error message to be more specific when no files are found as listed in as listed in PKG-INFO. (#5381)
- Always read ``pyproject.toml`` as UTF-8. This fixes Unicode handling on Windows and Python 2. (#5482)
- Fix a crash that occurs when PATH not set, while generating script location warning. (#5558)
- Disallow packages with ``pyproject.toml`` files that have an empty build-system table. (#5627)

Vendored Libraries
------------------

- Update CacheControl to 0.12.5.
- Update certifi to 2018.4.16.
- Update distro to 1.3.0.
- Update idna to 2.7.
- Update ipaddress to 1.0.22.
- Update pkg_resources to 39.2.0 (via setuptools).
- Update progress to 1.4.
- Update pytoml to 0.1.16.
- Update requests to 2.19.1.
- Update urllib3 to 1.23.

Improved Documentation
----------------------

- Document how to use pip with a proxy server. (#512, #5574)
- Document that the output of pip show is in RFC-compliant mail header format. (#5261)


10.0.1 (2018-04-19)
===================

Features
--------

- Switch the default repository to the new "PyPI 2.0" running at
  https://pypi.org/. (#5214)

Bug Fixes
---------

- Fix a bug that made get-pip.py unusable on Windows without renaming. (#5219)
- Fix a TypeError when loading the cache on older versions of Python 2.7.
  (#5231)
- Fix and improve error message when EnvironmentError occurs during
  installation. (#5237)
- A crash when reinstalling from VCS requirements has been fixed. (#5251)
- Fix PEP 518 support when pip is installed in the user site. (#5524)

Vendored Libraries
------------------

- Upgrade distlib to 0.2.7


10.0.0 (2018-04-14)
===================

Bug Fixes
---------

- Prevent false-positive installation warnings due to incomplete name
  normalization. (#5134)
- Fix issue where installing from Git with a short SHA would fail. (#5140)
- Accept pre-release versions when checking for conflicts with pip check or pip
  install. (#5141)
- ``ioctl(fd, termios.TIOCGWINSZ, ...)`` needs 8 bytes of data (#5150)
- Do not warn about script location when installing to the directory containing
  sys.executable. This is the case when 'pip install'ing without activating a
  virtualenv. (#5157)
- Fix PEP 518 support. (#5188)
- Don't warn about script locations if ``--target`` is specified. (#5203)


10.0.0b2 (2018-04-02)
=====================

Bug Fixes
---------

- Fixed line endings in CA Bundle - 10.0.0b1 was inadvertently released with Windows
  line endings. (#5131)


10.0.0b1 (2018-03-31)
=====================

Deprecations and Removals
-------------------------

- Removed the deprecated ``--egg`` parameter to ``pip install``. (#1749)
- Removed support for uninstalling projects which have been installed using
  distutils. distutils installed projects do not include metadata indicating
  what files belong to that install and thus it is impossible to *actually*
  uninstall them rather than just remove the metadata saying they've been
  installed while leaving all of the actual files behind. (#2386)
- Removed the deprecated ``--download`` option to ``pip install``. (#2643)
- Removed the deprecated --(no-)use-wheel flags to ``pip install`` and ``pip
  wheel``. (#2699)
- Removed the deprecated ``--allow-external``, ``--allow-all-external``, and
  ``--allow-unverified`` options. (#3070)
- Switch the default for ``pip list`` to the columns format, and deprecate the
  legacy format. (#3654, #3686)
- Deprecate support for Python 3.3. (#3796)
- Removed the deprecated ``--default-vcs`` option. (#4052)
- Removed the ``setup.py test`` support from our sdist as it wasn't being
  maintained as a supported means to run our tests. (#4203)
- Dropped support for Python 2.6. (#4343)
- Removed the --editable flag from pip download, as it did not make sense
  (#4362)
- Deprecate SVN detection based on dependency links in ``pip freeze``. (#4449)
- Move all of pip's APIs into the pip._internal package, properly reflecting
  the fact that pip does not currently have any public APIs. (#4696, #4700)

Features
--------

- Add `--progress-bar <progress_bar>` to ``pip download``, ``pip install`` and
  ``pip wheel`` commands, to allow selecting a specific progress indicator or,
  to completely suppress, (for example in a CI environment) use
  ``--progress-bar off```. (#2369, #2756)
- Add `--no-color` to `pip`. All colored output is disabled if this flag is
  detected. (#2449)
- pip uninstall now ignores the absence of a requirement and prints a warning.
  (#3016, #4642)
- Improved the memory and disk efficiency of the HTTP cache. (#3515)
- Support for packages specifying build dependencies in pyproject.toml (see
  `PEP 518 <https://www.python.org/dev/peps/pep-0518/>`__). Packages which
  specify one or more build dependencies this way will be built into wheels in
  an isolated environment with those dependencies installed. (#3691)
- pip now supports environment variable expansion in requirement files using
  only ``${VARIABLE}`` syntax on all platforms. (#3728)
- Allowed combinations of -q and -v to act sanely. Then we don't need warnings
  mentioned in the issue. (#4008)
- Add `--exclude-editable` to ``pip freeze`` and ``pip list`` to exclude
  editable packages from installed package list. (#4015, #4016)
- Improve the error message for the common ``pip install ./requirements.txt``
  case. (#4127)
- Add support for the new ``@ url`` syntax from PEP 508. (#4175)
- Add setuptools version to the statistics sent to BigQuery. (#4209)
- Report the line which caused the hash error when using requirement files.
  (#4227)
- Add a pip config command for managing configuration files. (#4240)
- Allow ``pip download`` to be used with a specific platform when ``--no-deps``
  is set. (#4289)
- Support build-numbers in wheel versions and support sorting with
  build-numbers. (#4299)
- Change pip outdated to use PackageFinder in order to do the version lookup so
  that local mirrors in Environments that do not have Internet connections can
  be used as the Source of Truth for latest version. (#4336)
- pip now retries on more HTTP status codes, for intermittent failures.
  Previously, it only retried on the standard 503. Now, it also retries on 500
  (transient failures on AWS S3), 520 and 527 (transient failures on
  Cloudflare). (#4473)
- pip now displays where it is looking for packages, if non-default locations
  are used. (#4483)
- Display a message to run the right command for modifying pip on Windows
  (#4490)
- Add Man Pages for pip (#4491)
- Make uninstall command less verbose by default (#4493)
- Switch the default upgrade strategy to be 'only-if-needed' (#4500)
- Installing from a local directory or a VCS URL now builds a wheel to install,
  rather than running ``setup.py install``. Wheels from these sources are not
  cached. (#4501)
- Don't log a warning when installing a dependency from Git if the name looks
  like a commit hash. (#4507)
- pip now displays a warning when it installs scripts from a wheel outside the
  PATH. These warnings can be suppressed using a new --no-warn-script-location
  option. (#4553)
- Local Packages can now be referenced using forward slashes on Windows.
  (#4563)
- pip show learnt a new Required-by field that lists currently installed
  packages that depend on the shown package (#4564)
- The command-line autocompletion engine ``pip show`` now autocompletes
  installed distribution names. (#4749)
- Change documentation theme to be in line with Python Documentation (#4758)
- Add auto completion of short options. (#4954)
- Run 'setup.py develop' inside pep518 build environment. (#4999)
- pip install now prints an error message when it installs an incompatible
  version of a dependency. (#5000)
- Added a way to distinguish between pip installed packages and those from the
  system package manager in 'pip list'. Specifically, 'pip list -v' also shows
  the installer of package if it has that meta data. (#949)
- Show install locations when list command ran with "-v" option. (#979)

Bug Fixes
---------

- Allow pip to work if the ``GIT_DIR`` and ``GIT_WORK_TREE`` environment
  variables are set. (#1130)
- Make ``pip install --force-reinstall`` not require passing ``--upgrade``.
  (#1139)
- Return a failing exit status when `pip install`, `pip download`, or `pip
  wheel` is called with no requirements. (#2720)
- Interactive setup.py files will no longer hang indefinitely. (#2732, #4982)
- Correctly reset the terminal if an exception occurs while a progress bar is
  being shown. (#3015)
- "Support URL-encoded characters in URL credentials." (#3236)
- Don't assume sys.__stderr__.encoding exists (#3356)
- Fix ``pip uninstall`` when ``easy-install.pth`` lacks a trailing newline.
  (#3741)
- Keep install options in requirements.txt from leaking. (#3763)
- pip no longer passes global options from one package to later packages in the
  same requirement file. (#3830)
- Support installing from Git refs (#3876)
- Use pkg_resources to parse the entry points file to allow names with colons.
  (#3901)
- ``-q`` specified once correctly sets logging level to WARNING, instead of
  CRITICAL. Use `-qqq` to have the previous behavior back. (#3994)
- Shell completion scripts now use correct executable names (e.g., ``pip3``
  instead of ``pip``) (#3997)
- Changed vendored encodings from ``utf8`` to ``utf-8``. (#4076)
- Fixes destination directory of data_files when ``pip install --target`` is
  used. (#4092)
- Limit the disabling of requests' pyopenssl to Windows only. Fixes
  "SNIMissingWarning / InsecurePlatformWarning not fixable with pip 9.0 /
  9.0.1" (for non-Windows) (#4098)
- Support the installation of wheels with non-PEP 440 version in their
  filenames. (#4169)
- Fall back to sys.getdefaultencoding() if locale.getpreferredencoding()
  returns None in `pip.utils.encoding.auto_decode`. (#4184)
- Fix a bug where `SETUPTOOLS_SHIM` got called incorrectly for relative path
  requirements by converting relative paths to absolute paths prior to calling
  the shim. (#4208)
- Return the latest version number in search results. (#4219)
- Improve error message on permission errors (#4233)
- Fail gracefully when ``/etc/image_version`` (or another distro version file)
  appears to exists but is not readable. (#4249)
- Avoid importing setuptools in the parent pip process, to avoid a race
  condition when upgrading one of setuptools dependencies. (#4264)
- Fix for an incorrect ``freeze`` warning message due to a package being
  included in multiple requirements files that were passed to ``freeze``.
  Instead of warning incorrectly that the package is not installed, pip now
  warns that the package was declared multiple times and lists the name of each
  requirements file that contains the package in question. (#4293)
- Generalize help text for ``compile``/``no-compile`` flags. (#4316)
- Handle the case when ``/etc`` is not readable by the current user by using a
  hardcoded list of possible names of release files. (#4320)
- Fixed a ``NameError`` when attempting to catch ``FileNotFoundError`` on
  Python 2.7. (#4322)
- Ensure USER_SITE is correctly initialised. (#4437)
- Reinstalling an editable package from Git no longer assumes that the
  ``master`` branch exists. (#4448)
- This fixes an issue where when someone who tries to use git with pip but pip
  can't because git is not in the path environment variable. This clarifies the
  error given to suggest to the user what might be wrong. (#4461)
- Improve handling of text output from build tools (avoid Unicode errors)
  (#4486)
- Fix a "No such file or directory" error when using --prefix. (#4495)
- Allow commands to opt out of --require-venv. This allows pip help to work
  even when the environment variable PIP_REQUIRE_VIRTUALENV is set. (#4496)
- Fix warning message on mismatched versions during installation. (#4655)
- pip now records installed files in a deterministic manner improving
  reproducibility. (#4667)
- Fix an issue where ``pip install -e`` on a Git url would fail to update if a
  branch or tag name is specified that happens to match the prefix of the
  current ``HEAD`` commit hash. (#4675)
- Fix an issue where a variable assigned in a try clause was accessed in the
  except clause, resulting in an undefined variable error in the except clause.
  (#4811)
- Use log level `info` instead of `warning` when ignoring packages due to
  environment markers. (#4876)
- Replaced typo mistake in subversion support. (#4908)
- Terminal size is now correctly inferred when using Python 3 on Windows.
  (#4966)
- Abort if reading configuration causes encoding errors. (#4976)
- Add a ``--no-user`` option and use it when installing build dependencies.
  (#5085)

Vendored Libraries
------------------

- Upgraded appdirs to 1.4.3.
- Upgraded CacheControl to 0.12.3.
- Vendored certifi at 2017.7.27.1.
- Vendored chardet at 3.0.4.
- Upgraded colorama to 0.3.9.
- Upgraded distlib to 0.2.6.
- Upgraded distro to 1.2.0.
- Vendored idna at idna==2.6.
- Upgraded ipaddress to 1.0.18.
- Vendored msgpack-python at 0.4.8.
- Removed the vendored ordereddict.
- Upgraded progress to 1.3.
- Upgraded pyparsing to 2.2.0.
- Upgraded pytoml to 0.1.14.
- Upgraded requests to 2.18.4.
- Upgraded pkg_resources (via setuptools) to 36.6.0.
- Upgraded six to 1.11.0.
- Vendored urllib3 at 1.22.
- Upgraded webencodings to 0.5.1.

Improved Documentation
----------------------

- Added documentation on usage of --build command line option (#4262)
-  (#4358)
- Document how to call pip from your code, including the fact that we do not
  provide a Python API. (#4743)


9.0.3 (2018-03-21)
==================

- Fix an error where the vendored requests was not correctly containing itself
  to only the internal vendored prefix.
- Restore compatibility with 2.6.


9.0.2 (2018-03-16)
==================

- Fallback to using SecureTransport on macOS when the linked OpenSSL is too old
  to support TLSv1.2.


9.0.1 (2016-11-06)
==================

- Correct the deprecation message when not specifying a --format so that it
  uses the correct setting name (``format``) rather than the incorrect one
  (``list_format``). (#4058)
- Fix ``pip check`` to check all available distributions and not just the
  local ones. (#4083)
- Fix a crash on non ASCII characters from `lsb_release`. (#4062)
- Fix an SyntaxError in an unused module of a vendored dependency. (#4059)
- Fix UNC paths on Windows. (#4064)


9.0.0 (2016-11-02)
==================

- **BACKWARD INCOMPATIBLE** Remove the attempted autodetection of requirement
  names from URLs, URLs must include a name via ``#egg=``.
- **DEPRECATION** ``pip install --egg`` have been deprecated and will be
  removed in the future. This "feature" has a long list of drawbacks which
  break nearly all of pip's other features in subtle and hard-to-diagnose
  ways.
- **DEPRECATION** ``--default-vcs`` option. (#4052)
- **WARNING** pip 9 cache can break forward compatibility with previous pip
  versions if your package repository allows chunked responses. (#4078)
- Add an ``--upgrade-strategy`` option to ``pip install``, to control how
  dependency upgrades are managed. (#3972)
- Add a ``pip check`` command to check installed packages dependencies. (#3750)
- Add option allowing user to abort pip operation if file/directory exists
- Add Appveyor CI
- Uninstall existing packages when performing an editable installation of
  the same packages. (#1548)
- ``pip show`` is less verbose by default. ``--verbose`` prints multiline
  fields. (#3858)
- Add optional column formatting to ``pip list``. (#3651)
- Add ``--not-required`` option to ``pip list``, which lists packages that are
  not dependencies of other packages.
- Fix builds on systems with symlinked ``/tmp`` directory for custom
  builds such as numpy. (#3701)
- Fix regression in ``pip freeze``: when there is more than one git remote,
  priority is given to the remote named ``origin``. (#3708, #3616).
- Fix crash when calling ``pip freeze`` with invalid requirement installed.
  (#3704, #3681)
- Allow multiple ``--requirement`` files in ``pip freeze``. (#3703)
- Implementation of pep-503 ``data-requires-python``. When this field is
  present for a release link, pip will ignore the download when
  installing to a Python version that doesn't satisfy the requirement.
- ``pip wheel`` now works on editable packages too (it was only working on
  editable dependencies before); this allows running ``pip wheel`` on the result
  of ``pip freeze`` in presence of editable requirements. (#3695, #3291)
- Load credentials from ``.netrc`` files. (#3715, #3569)
- Add ``--platform``, ``--python-version``, ``--implementation`` and ``--abi``
  parameters to ``pip download``. These allow utilities and advanced users to
  gather distributions for interpreters other than the one pip is being run on.
  (#3760)
- Skip scanning virtual environments, even when venv/bin/python is a dangling
  symlink.
- Added ``pip completion`` support for the ``fish`` shell.
- Fix problems on Windows on Python 2 when username or hostname contains
  non-ASCII characters. (#3463, #3970, #4000)
- Use ``git fetch --tags`` to fetch tags in addition to everything else that
  is normally fetched; this is necessary in case a git requirement url
  points to a tag or commit that is not on a branch. (#3791)
- Normalize package names before using in ``pip show`` (#3976)
- Raise when Requires-Python do not match the running version and add
  ``--ignore-requires-python`` option as escape hatch. (#3846)
- Report the correct installed version when performing an upgrade in some
  corner cases. (#2382
- Add ``-i`` shorthand for ``--index`` flag in ``pip search``.
- Do not optionally load C dependencies in requests. (#1840, #2930, #3024)
- Strip authentication from SVN url prior to passing it to ``svn``.
  (#3697, #3209)
- Also install in platlib with ``--target`` option. (#3694, #3682)
- Restore the ability to use inline comments in requirements files passed to
  ``pip freeze``. (#3680)


8.1.2 (2016-05-10)
==================

- Fix a regression on systems with uninitialized locale. (#3575)
- Use environment markers to filter packages before determining if a required
  wheel is supported. (#3254)
- Make glibc parsing for `manylinux1` support more robust for the variety of
  glibc versions found in the wild. (#3588)
- Update environment marker support to fully support legacy and PEP 508 style
  environment markers. (#3624)
- Always use debug logging to the ``--log`` file. (#3351)
- Don't attempt to wrap search results for extremely narrow terminal windows.
  (#3655)


8.1.1 (2016-03-17)
==================

- Fix regression with non-ascii requirement files on Python 2 and add support
  for encoding headers in requirement files. (#3548, #3547)


8.1.0 (2016-03-05)
==================

- Implement PEP 513, which adds support for the manylinux1 platform tag,
  allowing carefully compiled binary wheels to be installed on compatible Linux
  platforms.
- Allow wheels which are not specific to a particular Python interpreter but
  which are specific to a particular platform. (#3202)
- Fixed an issue where ``call_subprocess`` would crash trying to print debug
  data on child process failure. (#3521, #3522)
- Exclude the wheel package from the `pip freeze` output (like pip and
  setuptools). (#2989)
- Allow installing modules from a subdirectory of a vcs repository in
  non-editable mode. (#3217, #3466)
- Make pip wheel and pip download work with vcs urls with subdirectory option.
  (#3466)
- Show classifiers in ``pip show``.
- Show PEP376 Installer in ``pip show``. (#3517)
- Unhide completion command. (#1810)
- Show latest version number in ``pip search`` results. (#1415)
- Decode requirement files according to their BOM if present. (#3485, #2865)
- Fix and deprecate package name detection from url path. (#3523, #3495)
- Correct the behavior where interpreter specific tags (such as cp34) were
  being used on later versions of the same interpreter instead of only for that
  specific interpreter. (#3472)
- Fix an issue where pip would erroneously install a 64 bit wheel on a 32 bit
  Python running on a 64 bit macOS machine.
- Do not assume that all git repositories have an origin remote.
- Correctly display the line to add to a requirements.txt for an URL based
  dependency when ``--require-hashes`` is enabled.


8.0.3 (2016-02-25)
==================

- Make ``install --quiet`` really quiet. (#3418)
- Fix a bug when removing packages in python 3: disable INI-style parsing of the
  entry_point.txt file to allow entry point names with colons. (#3434)
- Normalize generated script files path in RECORD files. (#3448)
- Fix bug introduced in 8.0.0 where subcommand output was not shown,
  even when the user specified ``-v`` / ``--verbose``. (#3486)
- Enable python -W with respect to PipDeprecationWarning. (#3455)
- Upgrade distlib to 0.2.2.
- Improved support for Jython when quoting executables in output scripts.
  (#3467)
- Add a `--all` option to `pip freeze` to include usually skipped package
  (like pip, setuptools and wheel) to the freeze output. (#1610)


8.0.2 (2016-01-21)
==================

- Stop attempting to trust the system CA trust store because it's extremely
  common for them to be broken, often in incompatible ways. (#3416)


8.0.1 (2016-01-21)
==================

- Detect CAPaths in addition to CAFiles on platforms that provide them.
- Installing argparse or wsgiref will no longer warn or error - pip will allow
  the installation even though it may be useless (since the installed thing
  will be shadowed by the standard library).
- Upgrading a distutils installed item that is installed outside of a virtual
  environment, while inside of a virtual environment will no longer warn or
  error.
- Fix a bug where pre-releases were showing up in ``pip list --outdated``
  without the ``--pre`` flag.
- Switch the SOABI emulation from using RuntimeWarnings to debug logging.
- Rollback the removal of the ability to uninstall distutils installed items
  until a future date.


8.0.0 (2016-01-19)
==================

- **BACKWARD INCOMPATIBLE** Drop support for Python 3.2.
- **BACKWARD INCOMPATIBLE** Remove the ability to find any files other than the
  ones directly linked from the index or find-links pages.
- **BACKWARD INCOMPATIBLE** Remove the ``--download-cache`` which had been
  deprecated and no-op'd in 6.0.
- **BACKWARD INCOMPATIBLE** Remove the ``--log-explicit-levels`` which had been
  deprecated in 6.0.
- **BACKWARD INCOMPATIBLE** Change pip wheel --wheel-dir default path from
  <cwd>/wheelhouse to <cwd>.
- Deprecate and no-op the ``--allow-external``, ``--allow-all-external``, and
  ``--allow-unverified`` functionality that was added as part of PEP 438. With
  changes made to the repository protocol made in PEP 470, these options are no
  longer functional.
- Allow ``--trusted-host`` within a requirements file. (#2822)
- Allow ``--process-dependency-links`` within a requirements file. (#1274)
- Allow ``--pre`` within a requirements file. (#1273)
- Allow repository URLs with secure transports to count as trusted. (E.g.,
  "git+ssh" is okay.) (#2811)
- Implement a top-level ``pip download`` command and deprecate
  ``pip install --download``.
- When uninstalling, look for the case of paths containing symlinked
  directories (#3141, #3154)
- When installing, if building a wheel fails, clear up the build directory
  before falling back to a source install. (#3047)
- Fix user directory expansion when ``HOME=/``. Workaround for Python bug
  https://bugs.python.org/issue14768. (#2996)
- Correct reporting of requirements file line numbers. (#3009, #3125)
- Fixed Exception(IOError) for ``pip freeze`` and ``pip list`` commands with
  subversion >= 1.7. (#1062, #3346)
- Provide a spinner showing that progress is happening when installing or
  building a package via ``setup.py``. This will alleviate concerns that
  projects with unusually long build times have with pip appearing to stall.
- Include the functionality of ``peep`` into pip, allowing hashes to be baked
  into a requirements file and ensuring that the packages being downloaded
  match one of those hashes. This is an additional, opt-in security measure
  that, when used, removes the need to trust the repository.
- Fix a bug causing pip to not select a wheel compiled against an OSX SDK later
  than what Python itself was compiled against when running on a newer version
  of OSX.
- Add a new ``--prefix`` option for ``pip install`` that supports wheels and
  sdists. (#3252)
- Fixed issue regarding wheel building with setup.py using a different encoding
  than the system. (#2042)
- Drop PasteScript specific egg_info hack. (#3270)
- Allow combination of pip list options --editable with --outdated/--uptodate.
  (#933)
- Gives VCS implementations control over saying whether a project is under
  their control. (#3258)
- Git detection now works when ``setup.py`` is not at the Git repo root
  and when ``package_dir`` is used, so ``pip freeze`` works in more
  cases. (#3258)
- Correctly freeze Git develop packages in presence of the &subdirectory
  option (#3258)
- The detection of editable packages now relies on the presence of ``.egg-link``
  instead of looking for a VCS, so ``pip list -e`` is more reliable. (#3258)
- Add the ``--prefix`` flag to ``pip install`` which allows specifying a root
  prefix to use instead of ``sys.prefix``. (#3252)
- Allow duplicate specifications in the case that only the extras differ, and
  union all specified extras together. (#3198)
- Fix the detection of the user's current platform on OSX when determining the
  OSX SDK version. (#3232)
- Prevent the automatically built wheels from mistakenly being used across
  multiple versions of Python when they may not be correctly configured for
  that by making the wheel specific to a specific version of Python and
  specific interpreter. (#3225)
- Emulate the SOABI support in wheels from Python 2.x on Python 2.x as closely
  as we can with the information available within the interpreter. (#3075)
- Don't roundtrip to the network when git is pinned to a specific commit hash
  and that hash already exists locally. (#3066)
- Prefer wheels built against a newer SDK to wheels built against an older SDK
  on OSX. (#3163)
- Show entry points for projects installed via wheel. (#3122)
- Improve message when an unexisting path is passed to --find-links option.
  (#2968)
- pip freeze does not add the VCS branch/tag name in the #egg=... fragment
  anymore. (#3312)
- Warn on installation of editable if the provided #egg=name part does not
  match the metadata produced by `setup.py egg_info`. (#3143)
- Add support for .xz files for python versions supporting them (>= 3.3). (#722)


7.1.2 (2015-08-22)
==================

- Don't raise an error if pip is not installed when checking for the latest pip
  version.


7.1.1 (2015-08-20)
==================

- Check that the wheel cache directory is writable before we attempt to write
  cached files to them.
- Move the pip version check until *after* any installs have been performed,
  thus removing the extraneous warning when upgrading pip.
- Added debug logging when using a cached wheel.
- Respect platlib by default on platforms that have it separated from purelib.
- Upgrade packaging to 15.3.
  - Normalize post-release spellings for rev/r prefixes.
- Upgrade distlib to 0.2.1.
  - Updated launchers to decode shebangs using UTF-8. This allows non-ASCII
  pathnames to be correctly handled.
  - Ensured that the executable written to shebangs is normcased.
  - Changed ScriptMaker to work better under Jython.
- Upgrade ipaddress to 1.0.13.


7.1.0 (2015-06-30)
==================

- Allow constraining versions globally without having to know exactly what will
  be installed by the pip command. (#2731)
- Accept --no-binary and --only-binary via pip.conf. (#2867)
- Allow ``--allow-all-external`` within a requirements file.
- Fixed an issue where ``--user`` could not be used when ``--prefix`` was used
  in a distutils configuration file.
- Fixed an issue where the SOABI tags were not correctly being generated on
  Python 3.5.
- Fixed an issue where we were advising windows users to upgrade by directly
  executing pip, when that would always fail on Windows.
- Allow ``~`` to be expanded within a cache directory in all situations.


7.0.3 (2015-06-01)
==================

- Fixed a regression where ``--no-cache-dir`` would raise an exception. (#2855)


7.0.2 (2015-06-01)
==================

- **BACKWARD INCOMPATIBLE** Revert the change (released in v7.0.0) that
  required quoting in requirements files around specifiers containing
  environment markers. (#2841)
- **BACKWARD INCOMPATIBLE** Revert the accidental introduction of support for
  options interleaved with requirements, version specifiers etc in
  ``requirements`` files. (#2841)
- Expand ``~`` in the cache directory when caching wheels. (#2816)
- Use ``python -m pip`` instead of ``pip`` when recommending an upgrade command
  to Windows users.


7.0.1 (2015-05-22)
==================

- Don't build and cache wheels for non-editable installations from VCSs.
- Allow ``--allow-all-external`` inside of a requirements.txt file, fixing a
  regression in 7.0.


7.0.0 (2015-05-21)
==================

- **BACKWARD INCOMPATIBLE** Removed the deprecated ``--mirror``,
  ``--use-mirrors``, and ``-M`` options.
- **BACKWARD INCOMPATIBLE** Removed the deprecated ``zip`` and ``unzip``
  commands.
- **BACKWARD INCOMPATIBLE** Removed the deprecated ``--no-install`` and
  ``--no-download`` options.
- **BACKWARD INCOMPATIBLE** No longer implicitly support an insecure origin
  origin, and instead require insecure origins be explicitly trusted with the
  ``--trusted-host`` option.
- **BACKWARD INCOMPATIBLE** Removed the deprecated link scraping that attempted
  to parse HTML comments for a specially formatted comment.
- **BACKWARD INCOMPATIBLE** Requirements in requirements files containing
  markers must now be quoted due to parser changes.  For example, use
  ``"SomeProject; python_version < '2.7'"``, not simply
  ``SomeProject; python_version < '2.7'`` (#2697, #2725)
- `get-pip.py` now installs the "wheel" package, when it's not already
  installed. (#2800)
- Ignores bz2 archives if Python wasn't compiled with bz2 support. (#497)
- Support ``--install-option`` and ``--global-option`` per requirement in
  requirement files. (#2537)
- Build Wheels prior to installing from sdist, caching them in the pip cache
  directory to speed up subsequent installs. (#2618)
- Allow fine grained control over the use of wheels and source builds. (#2699)
- ``--no-use-wheel`` and ``--use-wheel`` are deprecated in favour of new
  options ``--no-binary`` and ``--only-binary``. The equivalent of
  ``--no-use-wheel`` is ``--no-binary=:all:``. (#2699)
- The use of ``--install-option``, ``--global-option`` or ``--build-option``
  disable the use of wheels, and the autobuilding of wheels. (#2711, #2677)
- Improve logging when a requirement marker doesn't match your environment.
  (#2735)
- Removed the temporary modifications (that began in pip v1.4 when distribute
  and setuptools merged) that allowed distribute to be considered a conflict to
  setuptools. ``pip install -U setuptools`` will no longer upgrade "distribute"
  to "setuptools".  Instead, use ``pip install -U distribute``. (#2767)
- Only display a warning to upgrade pip when the newest version is a final
  release and it is not a post release of the version we already have
  installed. (#2766)
- Display a warning when attempting to access a repository that uses HTTPS when
  we don't have Python compiled with SSL support. (#2761)
- Allowing using extras when installing from a file path without requiring the
  use of an editable. (#2785)
- Fix an infinite loop when the cache directory is stored on a file system
  which does not support hard links. (#2796)
- Remove the implicit debug log that was written on every invocation, instead
  users will need to use ``--log`` if they wish to have one. (#2798)


6.1.1 (2015-04-07)
==================

- No longer ignore dependencies which have been added to the standard library,
  instead continue to install them.


6.1.0 (2015-04-07)
==================

- Fixes upgrades failing when no potential links were found for dependencies
  other than the current installation. (#2538, #2502)
- Use a smoother progress bar when the terminal is capable of handling it,
  otherwise fallback to the original ASCII based progress bar.
- Display much less output when `pip install` succeeds, because on success,
  users probably don't care about all the nitty gritty details of compiling and
  installing. When `pip install` fails, display the failed install output once
  instead of twice, because once is enough. (#2487)
- Upgrade the bundled copy of requests to 2.6.0, fixing CVE-2015-2296.
- Display format of latest package when using ``pip list --outdated``. (#2475)
- Don't use pywin32 as ctypes should always be available on Windows, using
  pywin32 prevented uninstallation of pywin32 on Windows. (:pull:`2467`)
- Normalize the ``--wheel-dir`` option, expanding out constructs such as ``~``
  when used. (#2441)
- Display a warning when an undefined extra has been requested. (#2142)
- Speed up installing a directory in certain cases by creating a sdist instead
  of copying the entire directory. (#2535)
- Don't follow symlinks when uninstalling files (#2552)
- Upgrade the bundled copy of cachecontrol from 0.11.1 to 0.11.2. (#2481, #2595)
- Attempt to more smartly choose the order of installation to try and install
  dependencies before the projects that depend on them. (#2616)
- Skip trying to install libraries which are part of the standard library.
  (#2636, #2602)
- Support arch specific wheels that are not tied to a specific Python ABI.
  (#2561)
- Output warnings and errors to stderr instead of stdout. (#2543)
- Adjust the cache dir file checks to only check ownership if the effective
  user is root. (#2396)
- Install headers into a per project name directory instead of all of them into
  the root directory when inside of a virtual environment. (#2421)


6.0.8 (2015-02-04)
==================

- Fix an issue where the ``--download`` flag would cause pip to no longer use
  randomized build directories.
- Fix an issue where pip did not properly unquote quoted URLs which contain
  characters like PEP 440's epoch separator (``!``).
- Fix an issue where distutils installed projects were not actually uninstalled
  and deprecate attempting to uninstall them altogether.
- Retry deleting directories in case a process like an antivirus is holding the
  directory open temporarily.
- Fix an issue where pip would hide the cursor on Windows but would not reshow
  it.


6.0.7 (2015-01-28)
==================

- Fix a regression where Numpy requires a build path without symlinks to
  properly build.
- Fix a broken log message when running ``pip wheel`` without a requirement.
- Don't mask network errors while downloading the file as a hash failure.
- Properly create the state file for the pip version check so it only happens
  once a week.
- Fix an issue where switching between Python 3 and Python 2 would evict cached
  items.
- Fix a regression where pip would be unable to successfully uninstall a
  project without a normalized version.


6.0.6 (2015-01-03)
==================

- Continue the regression fix from 6.0.5 which was not a complete fix.


6.0.5 (2015-01-03)
==================

- Fix a regression with 6.0.4 under Windows where most commands would raise an
  exception due to Windows not having the ``os.geteuid()`` function.


6.0.4 (2015-01-03)
==================

- Fix an issue where ANSI escape codes would be used on Windows even though the
  Windows shell does not support them, causing odd characters to appear with
  the progress bar.
- Fix an issue where using -v would cause an exception saying
  ``TypeError: not all arguments converted during string formatting``.
- Fix an issue where using -v with dependency links would cause an exception
  saying ``TypeError: 'InstallationCandidate' object is not iterable``.
- Fix an issue where upgrading distribute would cause an exception saying
  ``TypeError: expected string or buffer``.
- Show a warning and disable the use of the cache directory when the cache
  directory is not owned by the current user, commonly caused by using ``sudo``
  without the ``-H`` flag.
- Update PEP 440 support to handle the latest changes to PEP 440, particularly
  the changes to ``>V`` and ``<V`` so that they no longer imply ``!=V.*``.
- Document the default cache directories for each operating system.
- Create the cache directory when the pip version check needs to save to it
  instead of silently logging an error.
- Fix a regression where the ``-q`` flag would not properly suppress the
  display of the progress bars.


6.0.3 (2014-12-23)
==================

- Fix an issue where the implicit version check new in pip 6.0 could cause pip
  to block for up to 75 seconds if PyPI was not accessible.
- Make ``--no-index`` imply ``--disable-pip-version-check``.


6.0.2 (2014-12-23)
==================

- Fix an issue where the output saying that a package was installed would
  report the old version instead of the new version during an upgrade.
- Fix left over merge conflict markers in the documentation.
- Document the backwards incompatible PEP 440 change in the 6.0.0 changelog.


6.0.1 (2014-12-22)
==================

- Fix executable file permissions for Wheel files when using the distutils
  scripts option.
- Fix a confusing error message when an exceptions was raised at certain
  points in pip's execution.
- Fix the missing list of versions when a version cannot be found that matches
  the specifiers.
- Add a warning about the possibly problematic use of > when the given
  specifier doesn't match anything.
- Fix an issue where installing from a directory would not copy over certain
  directories which were being excluded, however some build systems rely on
  them.


6.0 (2014-12-22)
================

- **PROCESS** Version numbers are now simply ``X.Y`` where the leading ``1``
  has been dropped.
- **BACKWARD INCOMPATIBLE** Dropped support for Python 3.1.
- **BACKWARD INCOMPATIBLE** Removed the bundle support which was deprecated in
  1.4. (#1806)
- **BACKWARD INCOMPATIBLE** File lists generated by `pip show -f` are now
  rooted at the location reported by show, rather than one (unstated)
  directory lower. (#1933)
- **BACKWARD INCOMPATIBLE** The ability to install files over the FTP protocol
  was accidentally lost in pip 1.5 and it has now been decided to not restore
  that ability.
- **BACKWARD INCOMPATIBLE** PEP 440 is now fully implemented, this means that
  in some cases versions will sort differently or version specifiers will be
  interpreted differently than previously. The common cases should all function
  similarly to before.
- **DEPRECATION** ``pip install --download-cache`` and
  ``pip wheel --download-cache`` command line flags have been deprecated and
  the functionality removed. Since pip now automatically configures and uses
  it's internal HTTP cache which supplants the ``--download-cache`` the
  existing options have been made non functional but will still be accepted
  until their removal in pip v8.0. For more information please see
  https://pip.pypa.io/en/stable/reference/pip_install.html#caching
- **DEPRECATION** ``pip install --build`` and ``pip install --no-clean`` are now
  *NOT* deprecated.  This reverses the deprecation that occurred in v1.5.3.
  (#906)
- **DEPRECATION** Implicitly accessing URLs which point to an origin which is
  not a secure origin, instead requiring an opt-in for each host using the new
  ``--trusted-host`` flag (``pip install --trusted-host example.com foo``).
- Allow the new ``--trusted-host`` flag to also disable TLS verification for
  a particular hostname.
- Added a ``--user`` flag to ``pip freeze`` and ``pip list`` to check the
  user site directory only.
- Silence byte compile errors when installation succeed. (#1873)
- Added a virtualenv-specific configuration file. (#1364)
- Added site-wide configuration files. (1978)
- Added an automatic check to warn if there is an updated version of pip
  available. (#2049)
- `wsgiref` and `argparse` (for >py26) are now excluded from `pip list` and
  `pip freeze`. (#1606, #1369)
- Add ``--client-cert`` option for SSL client certificates. (#1424)
- `pip show --files` was broken for wheel installs. (#1635, #1484)
- install_lib should take precedence when reading distutils config.
  (#1642, #1641)
- Send `Accept-Encoding: identity` when downloading files in an attempt to
  convince some servers who double compress the downloaded file to stop doing
  so. (#1688)
- Stop breaking when given pip commands in uppercase (#1559, #1725)
- pip no longer adds duplicate logging consumers, so it won't create duplicate
  output when being called multiple times. (#1618, #1723)
- `pip wheel` now returns an error code if any wheels fail to build. (#1769)
- `pip wheel` wasn't building wheels for dependencies of editable requirements.
  (#1775)
- Allow the use of ``--no-use-wheel`` within a requirements file. (#1859)
- Attempt to locate system TLS certificates to use instead of the included
  CA Bundle if possible. (#1680, #1866)
- Allow use of Zip64 extension in Wheels and other zip files. (#1319, #1868)
- Properly handle an index or --find-links target which has a <base> without a
  href attribute. (#1101, #1869)
- Properly handle extras when a project is installed via Wheel. (#1885, #1896)
- Added support to respect proxies in ``pip search``.
  (#1180, #932, #1104, #1902)
- `pip install --download` works with vcs links. (#798, #1060, #1926)
- Disabled warning about insecure index host when using localhost. Based off of
  Guy Rozendorn's work in #1718. (#1456, #1967)
- Allow the use of OS standard user configuration files instead of ones simply
  based around ``$HOME``. (#2021)
- When installing directly from wheel paths or urls, previous versions were not
  uninstalled. (#1825, #804, #1838)
- Detect the location of the ``.egg-info`` directory by looking for any file
  located inside of it instead of relying on the record file listing a
  directory. (#2075, #2076)
- Use a randomized and secure default build directory when possible.
  (#1964, #1935, #676, #2122, CVE-2014-8991)
- Support environment markers in requirements.txt files. (#1433, #2134)
- Automatically retry failed HTTP requests by default. (#1444, #2147)
- Handle HTML Encoding better using a method that is more similar to how
  browsers handle it. (#1100, #1874)
- Reduce the verbosity of the pip command by default. (#2175, #2177, #2178)
- Fixed :issue:`2031` - Respect sys.executable on OSX when installing from
  Wheels.
- Display the entire URL of the file that is being downloaded when downloading
  from a non PyPI repository. (#2183)
- Support setuptools style environment markers in a source distribution. (#2153)


1.5.6 (2014-05-16)
==================

- Upgrade requests to 2.3.0 to fix an issue with proxies on Python 3.4.1.
  (#1821)


1.5.5 (2014-05-03)
==================

- Uninstall issues on debianized pypy, specifically issues with setuptools
  upgrades. (#1632, #1743)
- Update documentation to point at https://bootstrap.pypa.io/get-pip.py for
  bootstrapping pip.
- Update docs to point to https://pip.pypa.io/
- Upgrade the bundled projects (distlib==0.1.8, html5lib==1.0b3, six==1.6.1,
  colorama==0.3.1, setuptools==3.4.4).


1.5.4 (2014-02-21)
==================

- Correct deprecation warning for ``pip install --build`` to only notify when
  the `--build` value is different than the default.


1.5.3 (2014-02-20)
==================

- **DEPRECATION** ``pip install --build`` and ``pip install --no-clean`` are now
  deprecated. (#906)
- Fixed being unable to download directly from wheel paths/urls, and when wheel
  downloads did occur using requirement specifiers, dependencies weren't
  downloaded. (#1112, #1527)
- ``pip wheel`` was not downloading wheels that already existed. (#1320, #1524)
- ``pip install --download`` was failing using local ``--find-links``.
  (#1111, #1524)
- Workaround for Python bug https://bugs.python.org/issue20053. (#1544)
- Don't pass a unicode __file__ to setup.py on Python 2.x. (#1583)
- Verify that the Wheel version is compatible with this pip. (#1569)


1.5.2 (2014-01-26)
==================

- Upgraded the vendored ``pkg_resources`` and ``_markerlib`` to setuptools 2.1.
- Fixed an error that prevented accessing PyPI when pyopenssl, ndg-httpsclient,
  and pyasn1 are installed.
- Fixed an issue that caused trailing comments to be incorrectly included as
  part of the URL in a requirements file.


1.5.1 (2014-01-20)
==================

- pip now only requires setuptools (any setuptools, not a certain version) when
  installing distributions from src (i.e. not from wheel). (#1434)
- `get-pip.py` now installs setuptools, when it's not already installed. (#1475)
- Don't decode downloaded files that have a ``Content-Encoding`` header. (#1435)
- Fix to correctly parse wheel filenames with single digit versions. (#1445)
- If `--allow-unverified` is used assume it also means `--allow-external`.
  (#1457)


1.5 (2014-01-01)
================

- **BACKWARD INCOMPATIBLE** pip no longer supports the ``--use-mirrors``,
  ``-M``, and ``--mirrors`` flags. The mirroring support has been removed. In
  order to use a mirror specify it as the primary index with ``-i`` or
  ``--index-url``, or as an additional index with ``--extra-index-url``.
  (#1098, CVE-2013-5123)
- **BACKWARD INCOMPATIBLE** pip no longer will scrape insecure external urls by
  default nor will it install externally hosted files by default. Users may opt
  into installing externally hosted or insecure files or urls using
  ``--allow-external PROJECT`` and ``--allow-unverified PROJECT``. (#1055)
- **BACKWARD INCOMPATIBLE** pip no longer respects dependency links by default.
  Users may opt into respecting them again using ``--process-dependency-links``.
- **DEPRECATION** ``pip install --no-install`` and ``pip install
  --no-download`` are now formally deprecated.  See #906 for discussion on
  possible alternatives, or lack thereof, in future releases.
- **DEPRECATION** ``pip zip`` and ``pip unzip`` are now formally deprecated.
- pip will now install Mac OSX platform wheels from PyPI. (:pull:`1278`)
- pip now generates the appropriate platform-specific console scripts when
  installing wheels. (#1251)
- pip now confirms a wheel is supported when installing directly from a path or
  url. (#1315)
- ``--ignore-installed`` now behaves again as designed, after it was
  unintentionally broke in v0.8.3 when fixing #14. (#1097, #1352)
- Fixed a bug where global scripts were being removed when uninstalling --user
  installed packages. (#1353)
- ``--user`` wasn't being respected when installing scripts from wheels.
  (#1163, #1176)
- Assume '_' means '-' in versions from wheel filenames. (#1150, #1158)
- Error when using --log with a failed install. (#219, #1205)
- Fixed logging being buffered and choppy in Python 3. (#1131)
- Don't ignore --timeout. (#70, #1202)
- Fixed an error when setting PIP_EXISTS_ACTION. (#772, #1201)
- Added colors to the logging output in order to draw attention to important
  warnings and errors. (#1109)
- Added warnings when using an insecure index, find-link, or dependency link.
  (#1121)
- Added support for installing packages from a subdirectory using the
  ``subdirectory`` editable option. (#1082)
- Fixed "TypeError: bad operand type for unary" in some cases when installing
  wheels using --find-links. (#1192, #1218)
- Archive contents are now written based on system defaults and umask (i.e.
  permissions are not preserved), except that regular files with any execute
  permissions have the equivalent of "chmod +x" applied after being written.
  (#1133, #317, #1146)
- PreviousBuildDirError now returns a non-zero exit code and prevents the
  previous build dir from being cleaned in all cases. (#1162)
- Renamed --allow-insecure to --allow-unverified, however the old name will
  continue to work for a period of time. (#1257)
- Fixed an error when installing local projects with symlinks in Python 3.
  (#1006, #1311)
- The previously hidden ``--log-file`` option, is now shown as a general option.
  (#1316)


1.4.1 (2013-08-07)
==================

- **New Signing Key** Release 1.4.1 is using a different key than normal with
  fingerprint: 7C6B 7C5D 5E2B 6356 A926 F04F 6E3C BCE9 3372 DCFA
- Fixed issues with installing from pybundle files. (#1116)
- Fixed error when sysconfig module throws an exception. (#1095)
- Don't ignore already installed pre-releases. (#1076)
- Fixes related to upgrading setuptools. (#1092)
- Fixes so that --download works with wheel archives. (#1113)
- Fixes related to recognizing and cleaning global build dirs. (#1080)


1.4 (2013-07-23)
================

- **BACKWARD INCOMPATIBLE** pip now only installs stable versions by default,
  and offers a new ``--pre`` option to also find pre-release and development
  versions. (#834)
- **BACKWARD INCOMPATIBLE** Dropped support for Python 2.5. The minimum
  supported Python version for pip 1.4 is Python 2.6.
- Added support for installing and building wheel archives. Thanks Daniel Holth,
  Marcus Smith, Paul Moore, and Michele Lacchia (#845)
- Applied security patch to pip's ssl support related to certificate DNS
  wildcard matching (https://bugs.python.org/issue17980).
- To satisfy pip's setuptools requirement, pip now recommends setuptools>=0.8,
  not distribute. setuptools and distribute are now merged into one project
  called 'setuptools'. (#1003)
- pip will now warn when installing a file that is either hosted externally to
  the index or cannot be verified with a hash. In the future pip will default
  to not installing them and will require the flags --allow-external NAME, and
  --allow-insecure NAME respectively. (#985)
- If an already-downloaded or cached file has a bad hash, re-download it rather
  than erroring out. (#963)
- ``pip bundle`` and support for installing from pybundle files is now
  considered deprecated and will be removed in pip v1.5.
- Fix a number of issues related to cleaning up and not reusing build
  directories. (#413, #709, #634, #602, #939, #865, #948)
- Added a User Agent so that pip is identifiable in logs. (#901)
- Added ssl and --user support to get-pip.py. Thanks Gabriel de Perthuis.
  (#895)
- Fixed the proxy support, which was broken in pip 1.3.x (#840)
- Fixed pip failing when server does not send content-type header. Thanks
  Hugo Lopes Tavares and Kelsey Hightower. (#32, #872)
- "Vendorized" distlib as pip.vendor.distlib (https://distlib.readthedocs.io/).
- Fixed git VCS backend with git 1.8.3. (#967)


1.3.1 (2013-03-08)
==================

- Fixed a major backward incompatible change of parsing URLs to externally
  hosted packages that got accidentally included in 1.3.


1.3 (2013-03-07)
================

- SSL Cert Verification; Make https the default for PyPI access. Thanks
  James Cleveland, Giovanni Bajo, Marcus Smith and many others.
  (#791, CVE-2013-1629)
- Added "pip list" for listing installed packages and the latest version
  available. Thanks Rafael Caricio, Miguel Araujo, Dmitry Gladkov. (#752)
- Fixed security issues with pip's use of temp build directories.
  Thanks David (d1b) and Thomas Guttler. (#780, CVE-2013-1888)
- Improvements to sphinx docs and cli help. (#773)
- Fixed an issue dealing with macOS temp dir handling, which was causing global
  NumPy installs to fail. (#707, #768)
- Split help output into general vs command-specific option groups.
  Thanks Georgi Valkov. (#744, #721)
- Fixed dependency resolution when installing from archives with uppercase
  project names. (#724)
- Fixed problem where re-installs always occurred when using file:// find-links.
  (#683, #702)
- "pip install -v" now shows the full download url, not just the archive name.
  Thanks Marc Abramowitz (#687)
- Fix to prevent unnecessary PyPI redirects. Thanks Alex Gronholm (#695)
- Fixed an install failure under Python 3 when the same version of a package is
  found under 2 different URLs. Thanks Paul Moore (#670, #671)
- Fix git submodule recursive updates. Thanks Roey Berman. (#674)
- Explicitly ignore rel='download' links while looking for html pages. Thanks
  Maxime R. (#677)
- --user/--upgrade install options now work together. Thanks 'eevee' for
  discovering the problem. (#705)
- Added check in ``install --download`` to prevent re-downloading if the target
  file already exists. Thanks Andrey Bulgakov. (#669)
- Added support for bare paths (including relative paths) as argument to
  `--find-links`. Thanks Paul Moore for draft patch.
- Added support for --no-index in requirements files.
- Added "pip show" command to get information about an installed package.
  Thanks Kelsey Hightower and Rafael Caricio. (#131)
- Added `--root` option for "pip install" to specify root directory. Behaves
  like the same option in distutils but also plays nice with pip's egg-info.
  Thanks Przemek Wrzos. (#253, #693)


1.2.1 (2012-09-06)
==================

- Fixed a regression introduced in 1.2 about raising an exception when
  not finding any files to uninstall in the current environment. Thanks for
  the fix, Marcus Smith.


1.2 (2012-09-01)
================

- **Dropped support for Python 2.4** The minimum supported Python version is
  now Python 2.5.
- Fixed PyPI mirror support being broken on some DNS responses. Thanks
  philwhin. (#605)
- Fixed pip uninstall removing files it didn't install. Thanks pjdelport.
  (#355)
- Fixed a number of issues related to improving support for the user
  installation scheme. Thanks Marcus Smith. (#493, #494, #440, #573)
- Write failure log to temp file if default location is not writable. Thanks
  andreigc.
- Pull in submodules for git editable checkouts. Thanks Hsiaoming Yang and
  Markus Hametner. (#289, #421)
- Use a temporary directory as the default build location outside of a
  virtualenv. Thanks Ben Rosser. (#339, #381)
- Added support for specifying extras with local editables. Thanks Nick
  Stenning.
- Added ``--egg`` flag to request egg-style rather than flat installation.
  Thanks Kamal Bin Mustafa. (#3)
- Prevent e.g. ``gmpy2-2.0.tar.gz`` from matching a request to
  ``pip install gmpy``; sdist filename must begin with full project name
  followed by a dash. Thanks casevh for the report. (#510)
- Allow package URLS to have querystrings. Thanks W. Trevor King. (#504)
- pip freeze now falls back to non-editable format rather than blowing up if it
  can't determine the origin repository of an editable. Thanks Rory McCann.
  (#58)
- Added a `__main__.py` file to enable `python -m pip` on Python versions
  that support it. Thanks Alexey Luchko.
- Fixed upgrading from VCS url of project that does exist on index. Thanks
  Andrew Knapp for the report. (#487)
- Fix upgrade from VCS url of project with no distribution on index.
  Thanks Andrew Knapp for the report. (#486)
- Add a clearer error message on a malformed VCS url. Thanks Thomas Fenzl.
  (#427)
- Added support for using any of the built in guaranteed algorithms in
  ``hashlib`` as a checksum hash.
- Raise an exception if current working directory can't be found or accessed.
  (#321)
- Removed special casing of the user directory and use the Python default
  instead. (#82)
- Only warn about version conflicts if there is actually one. This re-enables
  using ``==dev`` in requirements files. (#436)
- Moved tests to be run on Travis CI: https://travis-ci.org/pypa/pip
- Added a better help formatter.


1.1 (2012-02-16)
================

- Don't crash when a package's setup.py emits UTF-8 and then fails. Thanks
  Marc Abramowitz. (#326)
- Added ``--target`` option for installing directly to arbitrary directory.
  Thanks Stavros Korokithakis.
- Added support for authentication with Subversion repositories. Thanks
  Qiangning Hong.
- ``--download`` now downloads dependencies as well. Thanks Qiangning Hong.
  (#315)
- Errors from subprocesses will display the current working directory.
  Thanks Antti Kaihola.
- Fixed  compatibility with Subversion 1.7. Thanks Qiangning Hong. Note that
  setuptools remains incompatible with Subversion 1.7; to get the benefits of
  pip's support you must use Distribute rather than setuptools. (#369)
- Ignore py2app-generated macOS mpkg zip files in finder. Thanks Rene Dudfield.
  (#57)
- Log to ~/Library/Logs/ by default on macOS framework installs. Thanks
  Dan Callahan for report and patch. (#182)
- Understand version tags without minor version ("py3") in sdist filenames.
  Thanks Stuart Andrews for report and Olivier Girardot for patch. (#310)
- pip now supports optionally installing setuptools "extras" dependencies; e.g.
  "pip install Paste[openid]". Thanks Matt Maker and Olivier Girardot. (#7)
- freeze no longer borks on requirements files with --index-url or --find-links.
  Thanks Herbert Pfennig. (#391)
- Handle symlinks properly. Thanks lebedov for the patch. (#288)
- pip install -U no longer reinstalls the same versions of packages. Thanks
  iguananaut for the pull request. (#49)
- Removed ``-E``/``--environment`` option and ``PIP_RESPECT_VIRTUALENV``;
  both use a restart-in-venv mechanism that's broken, and neither one is
  useful since every virtualenv now has pip inside it.  Replace ``pip -E
  path/to/venv install Foo`` with ``virtualenv path/to/venv &&
  path/to/venv/pip install Foo``.
- Fixed pip throwing an IndexError when it calls `scraped_rel_links`. (#366)
- pip search should set and return a useful shell status code. (#22)
- Added global ``--exists-action`` command line option to easier script file
  exists conflicts, e.g. from editable requirements from VCS that have a
  changed repo URL. (#351, #365)


1.0.2 (2011-07-16)
==================

- Fixed docs issues.
- Reinstall a package when using the ``install -I`` option. (#295)
- Finds a Git tag pointing to same commit as origin/master. (#283)
- Use absolute path for path to docs in setup.py. (#279)
- Correctly handle exceptions on Python3. (#314)
- Correctly parse ``--editable`` lines in requirements files. (#320)


1.0.1 (2011-04-30)
==================

- Start to use git-flow.
- `find_command` should not raise AttributeError. (#274)
- Respect Content-Disposition header. Thanks Bradley Ayers. (#273)
- pathext handling on Windows. (#233)
- svn+svn protocol. (#252)
- multiple CLI searches. (#44)
- Current working directory when running setup.py clean. (#266)


1.0 (2011-04-04)
================

- Added Python 3 support! Huge thanks to Vinay Sajip, Vitaly Babiy, Kelsey
  Hightower, and Alex Gronholm, among others.
- Download progress only shown on a real TTY. Thanks Alex Morega.
- Fixed finding of VCS binaries to not be fooled by same-named directories.
  Thanks Alex Morega.
- Fixed uninstall of packages from system Python for users of Debian/Ubuntu
  python-setuptools package (workaround until fixed in Debian and Ubuntu).
- Added `get-pip.py <https://raw.github.com/pypa/pip/master/contrib/get-pip.py>`_
  installer. Simply download and execute it, using the Python interpreter of
  your choice::

    $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    $ python get-pip.py

  This may have to be run as root.

  .. note::

      Make sure you have `distribute <http://pypi.python.org/pypi/distribute>`_
      installed before using the installer!


0.8.3
=====

- Moved main repository to GitHub: https://github.com/pypa/pip
- Transferred primary maintenance from Ian to Jannis Leidel, Carl Meyer,
  Brian Rosner
- Fixed no uninstall-on-upgrade with URL package. Thanks Oliver Tonnhofer.
  (#14)
- Fixed egg name not properly resolving. Thanks Igor Sobreira. (#163)
- Fixed Non-alphabetical installation of requirements. Thanks Igor Sobreira.
  (#178)
- Fixed documentation mentions --index instead of --index-url. Thanks
  Kelsey Hightower (#199)
- rmtree undefined in mercurial.py. Thanks Kelsey Hightower. (#204)
- Fixed bug in Git vcs backend that would break during reinstallation.
- Fixed bug in Mercurial vcs backend related to pip freeze and branch/tag
  resolution.
- Fixed bug in version string parsing related to the suffix "-dev".


0.8.2
=====

- Avoid redundant unpacking of bundles (from pwaller)
- Fixed checking out the correct tag/branch/commit when updating an editable
  Git requirement. (#32, #150, #161)
- Added ability to install version control requirements without making them
  editable, e.g.::

    pip install git+https://github.com/pypa/pip/

  (#49)
- Correctly locate build and source directory on macOS. (#175)
- Added ``git+https://`` scheme to Git VCS backend.


0.8.1
=====

- Added global --user flag as shortcut for --install-option="--user". From
  Ronny Pfannschmidt.
- Added support for `PyPI mirrors <http://pypi.python.org/mirrors>`_ as
  defined in `PEP 381 <https://www.python.org/dev/peps/pep-0381/>`_, from
  Jannis Leidel.
- Fixed git revisions being ignored. Thanks John-Scott Atlakson. (#138)
- Fixed initial editable install of github package from a tag failing. Thanks
  John-Scott Atlakson. (#95)
- Fixed installing if a directory in cwd has the same name as the package
  you're installing. (#107)
- --install-option="--prefix=~/.local" ignored with -e. Thanks
  Ronny Pfannschmidt and Wil Tan. (#39)


0.8
===

- Track which ``build/`` directories pip creates, never remove directories
  it doesn't create.  From Hugo Lopes Tavares.
- pip now accepts file:// index URLs. Thanks Dave Abrahams.
- Various cleanup to make test-running more consistent and less fragile.
  Thanks Dave Abrahams.
- Real Windows support (with passing tests). Thanks Dave Abrahams.
- ``pip-2.7`` etc. scripts are created (Python-version specific scripts)
- ``contrib/build-standalone`` script creates a runnable ``.zip`` form of
  pip, from Jannis Leidel
- Editable git repos are updated when reinstalled
- Fix problem with ``--editable`` when multiple ``.egg-info/`` directories
  are found.
- A number of VCS-related fixes for ``pip freeze``, from Hugo Lopes Tavares.
- Significant test framework changes, from Hugo Lopes Tavares.


0.7.2
=====

- Set zip_safe=False to avoid problems some people are encountering where
  pip is installed as a zip file.


0.7.1
=====

- Fixed opening of logfile with no directory name. Thanks Alexandre Conrad.
- Temporary files are consistently cleaned up, especially after
  installing bundles, also from Alex Conrad.
- Tests now require at least ScriptTest 1.0.3.


0.7
===

- Fixed uninstallation on Windows
- Added ``pip search`` command.
- Tab-complete names of installed distributions for ``pip uninstall``.
- Support tab-completion when there is a global-option before the
  subcommand.
- Install header files in standard (scheme-default) location when installing
  outside a virtualenv. Install them to a slightly more consistent
  non-standard location inside a virtualenv (since the standard location is
  a non-writable symlink to the global location).
- pip now logs to a central location by default (instead of creating
  ``pip-log.txt`` all over the place) and constantly overwrites the
  file in question. On Unix and macOS this is ``'$HOME/.pip/pip.log'``
  and on Windows it's ``'%HOME%\\pip\\pip.log'``. You are still able to
  override this location with the ``$PIP_LOG_FILE`` environment variable.
  For a complete (appended) logfile use the separate ``'--log'`` command line
  option.
- Fixed an issue with Git that left an editable package as a checkout of a
  remote branch, even if the default behaviour would have been fine, too.
- Fixed installing from a Git tag with older versions of Git.
- Expand "~" in logfile and download cache paths.
- Speed up installing from Mercurial repositories by cloning without
  updating the working copy multiple times.
- Fixed installing directly from directories (e.g.
  ``pip install path/to/dir/``).
- Fixed installing editable packages with ``svn+ssh`` URLs.
- Don't print unwanted debug information when running the freeze command.
- Create log file directory automatically. Thanks Alexandre Conrad.
- Make test suite easier to run successfully. Thanks Dave Abrahams.
- Fixed "pip install ." and "pip install .."; better error for directory
  without setup.py. Thanks Alexandre Conrad.
- Support Debian/Ubuntu "dist-packages" in zip command. Thanks duckx.
- Fix relative --src folder. Thanks Simon Cross.
- Handle missing VCS with an error message. Thanks Alexandre Conrad.
- Added --no-download option to install; pairs with --no-install to separate
  download and installation into two steps. Thanks Simon Cross.
- Fix uninstalling from requirements file containing -f, -i, or
  --extra-index-url.
- Leftover build directories are now removed. Thanks Alexandre Conrad.


0.6.3
=====

- Fixed import error on Windows with regard to the backwards compatibility
  package

0.6.2
=====

- Fixed uninstall when /tmp is on a different filesystem.
- Fixed uninstallation of distributions with namespace packages.


0.6.1
=====

- Added support for the ``https`` and ``http-static`` schemes to the
  Mercurial and ``ftp`` scheme to the Bazaar backend.
- Fixed uninstallation of scripts installed with easy_install.
- Fixed an issue in the package finder that could result in an
  infinite loop while looking for links.
- Fixed issue with ``pip bundle`` and local files (which weren't being
  copied into the bundle), from Whit Morriss.


0.6
===

- Add ``pip uninstall`` and uninstall-before upgrade (from Carl Meyer).
- Extended configurability with config files and environment variables.
- Allow packages to be upgraded, e.g., ``pip install Package==0.1``
  then ``pip install Package==0.2``.
- Allow installing/upgrading to Package==dev (fix "Source version does not
  match target version" errors).
- Added command and option completion for bash and zsh.
- Extended integration with virtualenv by providing an option to
  automatically use an active virtualenv and an option to warn if no active
  virtualenv is found.
- Fixed a bug with pip install --download and editable packages, where
  directories were being set with 0000 permissions, now defaults to 755.
- Fixed uninstallation of easy_installed console_scripts.
- Fixed uninstallation on macOS Framework layout installs
- Fixed bug preventing uninstall of editables with source outside venv.
- Creates download cache directory if not existing.


0.5.1
=====

- Fixed a couple little bugs, with git and with extensions.


0.5
===

- Added ability to override the default log file name (``pip-log.txt``)
  with the environmental variable ``$PIP_LOG_FILE``.
- Made the freeze command print installed packages to stdout instead of
  writing them to a file. Use simple redirection (e.g.
  ``pip freeze > stable-req.txt``) to get a file with requirements.
- Fixed problem with freezing editable packages from a Git repository.
- Added support for base URLs using ``<base href='...'>`` when parsing
  HTML pages.
- Fixed installing of non-editable packages from version control systems.
- Fixed issue with Bazaar's bzr+ssh scheme.
- Added --download-dir option to the install command to retrieve package
  archives. If given an editable package it will create an archive of it.
- Added ability to pass local file and directory paths to ``--find-links``,
  e.g. ``--find-links=file:///path/to/my/private/archive``
- Reduced the amount of console log messages when fetching a page to find a
  distribution was problematic. The full messages can be found in pip-log.txt.
- Added ``--no-deps`` option to install ignore package dependencies
- Added ``--no-index`` option to ignore the package index (PyPI) temporarily
- Fixed installing editable packages from Git branches.
- Fixes freezing of editable packages from Mercurial repositories.
- Fixed handling read-only attributes of build files, e.g. of Subversion and
  Bazaar on Windows.
- When downloading a file from a redirect, use the redirected
  location's extension to guess the compression (happens specifically
  when redirecting to a bitbucket.org tip.gz file).
- Editable freeze URLs now always use revision hash/id rather than tip or
  branch names which could move.
- Fixed comparison of repo URLs so incidental differences such as
  presence/absence of final slashes or quoted/unquoted special
  characters don't trigger "ignore/switch/wipe/backup" choice.
- Fixed handling of attempt to checkout editable install to a
  non-empty, non-repo directory.


0.4
===

- Make ``-e`` work better with local hg repositories
- Construct PyPI URLs the exact way easy_install constructs URLs (you
  might notice this if you use a custom index that is
  slash-sensitive).
- Improvements on Windows (from `Ionel Maries Cristian
  <https://ionelmc.wordpress.com/>`_).
- Fixed problem with not being able to install private git repositories.
- Make ``pip zip`` zip all its arguments, not just the first.
- Fix some filename issues on Windows.
- Allow the ``-i`` and ``--extra-index-url`` options in requirements
  files.
- Fix the way bundle components are unpacked and moved around, to make
  bundles work.
- Adds ``-s`` option to allow the access to the global site-packages if a
  virtualenv is to be created.
- Fixed support for Subversion 1.6.


0.3.1
=====

- Improved virtualenv restart and various path/cleanup problems on win32.
- Fixed a regression with installing from svn repositories (when not
  using ``-e``).
- Fixes when installing editable packages that put their source in a
  subdirectory (like ``src/``).
- Improve ``pip -h``


0.3
===

- Added support for editable packages created from Git, Mercurial and Bazaar
  repositories and ability to freeze them. Refactored support for version
  control systems.
- Do not use ``sys.exit()`` from inside the code, instead use a
  return.  This will make it easier to invoke programmatically.
- Put the install record in ``Package.egg-info/installed-files.txt``
  (previously they went in
  ``site-packages/install-record-Package.txt``).
- Fix a problem with ``pip freeze`` not including ``-e svn+`` when an
  svn structure is peculiar.
- Allow ``pip -E`` to work with a virtualenv that uses a different
  version of Python than the parent environment.
- Fixed Win32 virtualenv (``-E``) option.
- Search the links passed in with ``-f`` for packages.
- Detect zip files, even when the file doesn't have a ``.zip``
  extension and it is served with the wrong Content-Type.
- Installing editable from existing source now works, like ``pip
  install -e some/path/`` will install the package in ``some/path/``.
  Most importantly, anything that package requires will also be
  installed by pip.
- Add a ``--path`` option to ``pip un/zip``, so you can avoid zipping
  files that are outside of where you expect.
- Add ``--simulate`` option to ``pip zip``.


0.2.1
=====

- Fixed small problem that prevented using ``pip.py`` without actually
  installing pip.
- Fixed ``--upgrade``, which would download and appear to install
  upgraded packages, but actually just reinstall the existing package.
- Fixed Windows problem with putting the install record in the right
  place, and generating the ``pip`` script with Setuptools.
- Download links that include embedded spaces or other unsafe
  characters (those characters get %-encoded).
- Fixed use of URLs in requirement files, and problems with some blank
  lines.
- Turn some tar file errors into warnings.


0.2
===

- Renamed to ``pip``, and to install you now do ``pip install
  PACKAGE``
- Added command ``pip zip PACKAGE`` and ``pip unzip PACKAGE``.  This
  is particularly intended for Google App Engine to manage libraries
  to stay under the 1000-file limit.
- Some fixes to bundles, especially editable packages and when
  creating a bundle using unnamed packages (like just an svn
  repository without ``#egg=Package``).


0.1.4
=====

- Added an option ``--install-option`` to pass options to pass
  arguments to ``setup.py install``
- ``.svn/`` directories are no longer included in bundles, as these
  directories are specific to a version of svn -- if you build a
  bundle on a system with svn 1.5, you can't use the checkout on a
  system with svn 1.4.  Instead a file ``svn-checkout.txt`` is
  included that notes the original location and revision, and the
  command you can use to turn it back into an svn checkout.  (Probably
  unpacking the bundle should, maybe optionally, recreate this
  information -- but that is not currently implemented, and it would
  require network access.)
- Avoid ambiguities over project name case, where for instance
  MyPackage and mypackage would be considered different packages.
  This in particular caused problems on Macs, where ``MyPackage/`` and
  ``mypackage/`` are the same directory.
- Added support for an environmental variable
  ``$PIP_DOWNLOAD_CACHE`` which will cache package downloads, so
  future installations won't require large downloads.  Network access
  is still required, but just some downloads will be avoided when
  using this.


0.1.3
=====

- Always use ``svn checkout`` (not ``export``) so that
  ``tag_svn_revision`` settings give the revision of the package.
- Don't update checkouts that came from ``.pybundle`` files.


0.1.2
=====

- Improve error text when there are errors fetching HTML pages when
  seeking packages.
- Improve bundles: include empty directories, make them work with
  editable packages.
- If you use ``-E env`` and the environment ``env/`` doesn't exist, a
  new virtual environment will be created.
- Fix ``dependency_links`` for finding packages.


0.1.1
=====

- Fixed a NameError exception when running pip outside of a virtualenv
  environment.
- Added HTTP proxy support (from Prabhu Ramachandran)
- Fixed use of ``hashlib.md5`` on python2.5+ (also from Prabhu Ramachandran)


0.1
===

- Initial release
