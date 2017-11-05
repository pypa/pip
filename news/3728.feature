Add support for variable expansion in URLs in the requirement file. This allows
the use of URLs that require credentials to be used without storing the
credential as plain text in the requirement file. The variable format used is
limited to the POSIX-style `${MY_CREDENTIAL}`. An example pointing to an
installable artifact in a private Github repository looks like this::

    https://${GITHUB_TOKEN}:x-oauth-basic@github.com/the-user/my-repo/archive/master.zip
