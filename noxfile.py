"""Release time helpers, executed using nox.
"""

# The following comment should be removed at some point in the future.
# mypy: disallow-untyped-defs=False

import io
import subprocess

import nox


def get_author_list():
    """Get the list of authors from Git commits.
    """
    # subprocess because session.run doesn't give us stdout
    result = subprocess.run(
        ["git", "log", "--use-mailmap", "--format=%aN <%aE>"],
        capture_output=True,
        encoding="utf-8",
    )

    # Create a unique list.
    authors = []
    seen_authors = set()
    for author in result.stdout.splitlines():
        author = author.strip()
        if author.lower() not in seen_authors:
            seen_authors.add(author.lower())
            authors.append(author)

    # Sort our list of Authors by their case insensitive name
    return sorted(authors, key=lambda x: x.lower())


# -----------------------------------------------------------------------------
# Commands used during the release process
# -----------------------------------------------------------------------------
@nox.session
def generate_authors(session):
    # Get our list of authors
    session.log("Collecting author names")
    authors = get_author_list()

    # Write our authors to the AUTHORS file
    session.log("Writing AUTHORS")
    with io.open("AUTHORS.txt", "w", encoding="utf-8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


@nox.session
def generate_news(session):
    session.log("Generating NEWS")
    session.install("towncrier")

    # You can pass 2 possible arguments: --draft, --yes
    session.run("towncrier", *session.posargs)
