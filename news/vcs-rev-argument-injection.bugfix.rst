Reject VCS revisions that begin with a dash (``-``) when parsing a
``vcs+protocol://...@<revision>`` requirement, for all VCS backends (Git,
Mercurial, Bazaar and Subversion). Previously such a revision was passed
verbatim as a positional argument to the version control tool, where it was
interpreted as a command-line option rather than a revision. With Git this
allowed an attacker-controlled requirement to inject ``git fetch <url>
--upload-pack=<command>``, leading to arbitrary command execution for
local- or SSH-reachable transports. The revision is now validated before any
VCS subprocess is invoked.
