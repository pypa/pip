Validate the ``subdirectory`` fragment of a requirement URL when parsing a
link, rejecting values that are absolute paths, carry a drive letter, contain
control characters, or use ``..`` components to escape the project source
tree. Previously the fragment was joined onto the unpacked source directory
and used verbatim as the working directory for the build backend, so an
attacker-controlled requirement such as
``pkg @ https://example.com/pkg.tar.gz#subdirectory=../../../some/path`` could
point the build at files outside the extracted archive. Both the literal and
the percent-decoded form of the fragment are checked, under POSIX and Windows
path semantics, so encoded traversal sequences (``..%2F..``) cannot slip past
either. The fragment is now validated at the source (mirroring the existing
``egg`` fragment validation), and a defense-in-depth containment check is
enforced before the directory is handed to the build backend. This addresses a
path-traversal weakness (CWE-22) in the handling of requirement-URL fragments.
