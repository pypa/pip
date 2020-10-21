---
name: pip backtrack report
about: This template is for users who experience pip backtracking.
labels: ["K: UX", "C: new resolver", "C: dependency resolution"]
---

**Description**
With the release of the new resolver, pip is now more strict in the package versions it installs.

To communicate to users when (and why) pip backtracks, we've included [an INFO message during this backtracking](https://github.com/pypa/pip/issues/8975) in pip's output.

In this INFO message we ask users to file an issue about what packages pip backtracks on, how many times it occurs.

We'd appreciate if you answer these questions for us.

**Environment**

* pip version:
* Python version:
* OS:

<!-- Feel free to add more information about your environment here -->

**Description**
<!-- A short and concise description of why this backtracking occurred. -->

**How to Reproduce**
<!-- Describe the steps to reproduce this backtracking. -->

1. Get package from '...'
2. Then run '...'
3. Then backtracking occurs for `package-name` and `another-package-name`, etc.

**Output**
<!-- ``Most helpful is output that shows:
- what package you are installing when pip backtracks
- the multiple versions of packages that pip tries to install
- how many times does pip download those packages -->

```
Paste the output of the steps above, including the commands themselves etc.
```
