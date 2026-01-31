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
