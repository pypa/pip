import io

import invoke


@invoke.task
def authors(ctx):
    print("[generate.authors] Generating AUTHORS")

    # Get our list of authors
    print("[generate.authors] Collecting author names")

    # Note that it's necessary to use double quotes in the
    # --format"=%aN <%aE>" part of the command, as the Windows
    # shell doesn't recognise single quotes here.
    r = ctx.run('git log --use-mailmap --format"=%aN <%aE>"',
                encoding="utf-8", hide=True)

    authors = []
    seen_authors = set()
    for author in r.stdout.splitlines():
        author = author.strip()
        if author.lower() not in seen_authors:
            seen_authors.add(author.lower())
            authors.append(author)

    # Sort our list of Authors by their case insensitive name
    authors = sorted(authors, key=lambda x: x.lower())

    # Write our authors to the AUTHORS file
    print("[generate.authors] Writing AUTHORS")
    with io.open("AUTHORS.txt", "w", encoding="utf8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


@invoke.task
def news(ctx, draft=False, yes=False):
    print("[generate.news] Generating NEWS")

    args = []
    if draft:
        args.append("--draft")
    if yes:
        args.append("--yes")

    ctx.run("towncrier {}".format(" ".join(args)))
