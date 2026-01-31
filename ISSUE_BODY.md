This issue is to discuss the design and implementation of an `--index-mapping` feature in pip, as suggested in [PR #13773](https://github.com/pypa/pip/pull/13773).

### Motivation
Currently, pip's default behavior is to search all configured indexes and pick the highest version. This is vulnerable to "dependency confusion" attacks, where an internal package name is registered on a public index (like PyPI) with a higher version number. While `--index-strategy=first-match` helps, it's still based on search order.

### Proposal
Implement an `--index-mapping <PATTERN>:<URL>` option that allows users to explicitly bind package names (or wildcard patterns) to a specific index URL.

Example:
`pip install --index-mapping "acme-*:https://internal.repo/simple" acme-package`

If a mapping is defined:
1. Pip should ONLY look for matching packages in the specified index.
2. It should ignore all other indexes (even if they have higher versions).

### Design Considerations
- Interaction with `--find-links`.
- Supporting multiple mappings.
- Wilcard support (e.g. fnmatch style).
- Error behavior if a mapped index is unreachable or doesn't have the package.
