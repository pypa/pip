Remove vendored charset_normalizer.

Requests provides optional character detection support on some APIs
when processing ambiguous bytes. This isn't relevant for pip to function
and we're able to remove it due to recent upstream changes.
