# Self-referential extras

pip supports declaring optional dependencies that reference other optional dependencies of the same project.

Example:

```toml
[project.optional-dependencies]
all = ["pkg[a]", "pkg[b]"]
a = ["dependencyA"]
b = ["dependencyB"]
