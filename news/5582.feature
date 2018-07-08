Addition of ``--minor`` and ``--major`` flags to the pip freeze command.

For a given requirement, either will check if the version number of the package matches the PEP440 
versioning specification, assuming semantic versioning is followed.

- If `--minor` is applied, return the line `PACKAGE>=CURRENT,<MAJOR.MINOR+1.0`
- If `--major` is applied, return the line `PACKAGE>=CURRENT,<MAJOR+1.0.0`
- If a package that doesn't follow semver is found, the existing `==` syntax is used.

Both flags are disabled by default.