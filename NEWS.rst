.. NOTE: You should *NOT* be adding new change log entries to this file, this
         file is managed by towncrier. You *may* edit previous change logs to
         fix problems like typo corrections or such.

         To add a new change log entry, please see
             https://pip.pypa.io/en/latest/development/#adding-a-news-entry

.. towncrier release notes start


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
  http://bugs.python.org/issue14768. (#2996)
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
- Pip no longer adds duplicate logging consumers, so it won't create duplicate
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
- Workaround for Python bug http://bugs.python.org/issue20053. (#1544)
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
- Pip now confirms a wheel is supported when installing directly from a path or
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
  wildcard matching (http://bugs.python.org/issue17980).
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
- Fixed pypi mirror support being broken on some DNS responses. Thanks
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
- Moved tests to be run on Travis CI: http://travis-ci.org/pypa/pip
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
- Pip now supports optionally installing setuptools "extras" dependencies; e.g.
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

- Moved main repository to Github: https://github.com/pypa/pip
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
  defined in `PEP 381 <http://www.python.org/dev/peps/pep-0381/>`_, from
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
- Pip now accepts file:// index URLs. Thanks Dave Abrahams.
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
  <http://ionelmc.wordpress.com/>`_).
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
