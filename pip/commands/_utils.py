from __future__ import absolute_import
from pip.req import InstallRequirement, parse_requirements


class BadOptions(Exception):
    pass


def populate_requirement_set(
        requirement_set, args, options, logger, finder, session, name):
    """Marshal cmd line args into a requirement set.

    If no requirements are given an error is output to logger and an
    exception raised.

    :raises BadOptions: if no requirements are supplied.
    """
    # parse args and/or requirements files
    for name in args:
        requirement_set.add_requirement(
            InstallRequirement.from_line(
                name, None, isolated=options.isolated_mode,
            )
        )
    for name in options.editables:
        requirement_set.add_requirement(
            InstallRequirement.from_editable(
                name,
                default_vcs=options.default_vcs,
                isolated=options.isolated_mode,
            )
        )
    for filename in options.requirements:
        for req in parse_requirements(
                filename,
                finder=finder, options=options, session=session):
            requirement_set.add_requirement(req)
    if not requirement_set.has_requirements:
        opts = {'name': name}
        if options.find_links:
            msg = ('You must give at least one requirement to '
                   '%(name)s (maybe you meant "pip %(name)s '
                   '%(links)s"?)' %
                   dict(opts, links=' '.join(options.find_links)))
        else:
            msg = ('You must give at least one requirement '
                   'to %(name)s (see "pip help %(name)s")' % opts)
        logger.warning(msg)
        raise BadOptions()
