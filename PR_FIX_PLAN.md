# PR Fix Plan: Implement --index-strategy (#13773)

## Objective
Split the original PR into two separate features as requested by the maintainers. This PR will now focus exclusively on `--index-strategy`. The `--index-mapping` feature will be moved to a separate PR after design discussion.

## Changes Made
1.  **Code Cleanup**:
    *   Removed `--index-mapping` option from `src/pip/_internal/cli/cmdoptions.py`.
    *   Removed `index_mappings` from `SelectionPreferences` in `src/pip/_internal/models/selection_prefs.py`.
    *   Removed passing of `index_mappings` in `src/pip/_internal/cli/req_command.py`.
    *   Removed mapping logic and `_apply_index_mapping` method from `src/pip/_internal/index/package_finder.py`.
2.  **Focus on Strategy**:
    *   Ensured `--index-strategy` is the primary option (replacing the initial `--index-priority`).
    *   Maintained support for `best-match` (default) and `first-match` strategies.
3.  **Tests and Documentation**:
    *   Added comprehensive unit tests in `tests/unit/test_index_strategy.py`.
    *   Updated the User Guide in `docs/html/cli/pip_install.rst` to explain the new `--index-strategy` option.
4.  **News Fragment**:
    *   Updated `news/8606.feature.rst` to refer to `--index-strategy`.
    *   Deleted `news/50.feature.rst` (was for mapping).

## New PR Title
`Implement --index-strategy to mitigate dependency confusion (#8606)`

## New PR Description
This PR implements the `--index-strategy` feature to mitigate dependency confusion attacks, addressing #8606.

### Summary
`--index-strategy`: Controls how pip selects packages from multiple indexes.
- `best-match` (default): Standard pip behavior. Searches all indexes for the highest version.
- `first-match`: Prioritizes indexes in the order they are provided (`--index-url` then `--extra-index-url`). The search stops at the first index that yields a match.

### Motivation
The current "Version Priority" behavior exposes users to Dependency Confusion attacks. An attacker can upload a higher version of a private package name to a public repository, and pip will prioritize it. This feature provides a mechanism for users to enforce index isolation by stopping the search once a match is found.

### Design Details
- **Priority Order**: `find-links` are collected first. Then, we iterate through `--index-url` and `--extra-index-url` in order.
- **Stopping**: In `first-match` mode, the search stops as soon as one index URL returns candidates.

---

## Content for the new Issue (--index-mapping)
**Title**: [Feature] Implement --index-mapping for strict namespace isolation

**Body**:
This issue is to discuss the design and implementation of an `--index-mapping` feature in pip.

### Motivation
While `--index-strategy=first-match` helps, it's still based on search order. An `--index-mapping` feature would allow users to explicitly bind package names to specific indexes.

### Proposal
Add `--index-mapping <PATTERN>:<URL>`.
Example: `pip install --index-mapping 'acme-*:https://internal.repo/simple' acme-package`

If a mapping is defined, pip should ONLY look for matching packages in the specified index, ignoring all others.
