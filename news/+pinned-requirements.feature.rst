Speed up resolving requirements pinned with ``==``.

Only the index files of the pinned version are now evaluated. When resolution
fails, the list of versions ignored because they require a different Python
no longer includes releases of unrelated pinned packages.
