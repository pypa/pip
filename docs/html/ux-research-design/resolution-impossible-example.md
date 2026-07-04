---
orphan:
---

# Example error: ResolutionImpossible

## What if there are user-provided pinned packages?

Where a user wants to install packages (with 1 or more pinned version)
with default verbose level

```
$ pip install peach=1.0 apple=2.0

Due to conflicting dependencies pip cannot install Peach1.0 and Apple2.0:

* Peach 1.0 depends on Banana 3.0
* Apple2.0 depends on Banana2.0

There are a number of possible solutions. You can try:
1. removing package versions from your requirements, and letting pip try to resolve the problem for you
2. Trying  a version of Peach that depends on Banana2.0. Try `pip-search peach —dep banana2.0`
3. replacing Apple or Peach with a different package altogether
4. patching Apple2.0 to use Banana3.0
5. force installing (Be aware!)

For instructions on how to do these steps visit: https://pypa.io/SomeLink
To debug this further you can run `pip-tree` to see all of your dependencies.
```

**with verbose level -vv**

If a user ran the same pip command with more verbosity, what would they see?

**with verbose level -vvv**

If a user ran the same pip command with more verbosity, what would they see?

## What if there are no user-provided version restrictions?

NB: We are assuming this resolver behaviour gets implemented, based on [GH issues 8249](https://github.com/pypa/pip/issues/8249).

**with default verbose level**

```
$ pip install apple peach

Due to conflicting dependencies pip cannot install apple or peach. Both depend on banana, but pip can't find a version of either where they depend on the same banana version.

There are a number of possible solutions. You can try:
1. replacing apple or peach with a different package altogether
2. patching apple or peach to use the same version of banana
3. force installing (Be aware!)

To debug this further you can run pip-tree to see all of your dependencies.
```

**with verbose level -vv**

If a user ran the same pip command with more verbosity, what would they see?

**with verbose level -vvv**

If a user ran the same pip command with more verbosity, what would they see?

**What should be in the "documentation" page?**

* ways to swap a package for another
* how to patch a package to support a version (various ways)

## Recommendations

* Write official documentation / guide "How to resolve dependency conflicts" explaining:
  * Why conflicts can exist
  * How you can avoid them (pinning)
  * How you can resolve them
    * Use alternative package
    * Use older version
    * Patch package
* Introduce new commands to pip, inspired by poetry:
  * Tree: Show full tree of dependencies
  * Show `<package>` Show details of a package, including it's dependencies
  * latest - shows latest vs installed versions
  * outdated - shows only outdated versions
* Expose commands / help link in output??
  * when particular issue happens provide ways to move on (ala pipenv), e.g.
    * run this command to see X
    * is it your internet connection?
    * is it the pypi website?
* Aspirational commands
  * `pip search PackageName —dep PackageNameVersion`
    * a command that will search for a version of a package that has a dependency on another packageversion
