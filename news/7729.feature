Cache the result of parse_links() to avoid re-tokenizing a find-links page multiple times over a pip run.

This change significantly improves resolve performance when --find-links points to a very large html page.
