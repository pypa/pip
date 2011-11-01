import re
import sys
import pkg_resources
import pip
import json
from pip.req import InstallRequirement
from pip.log import logger
from pip.basecommand import Command
from pip.util import get_installed_distributions


class FreezeCommand(Command):
    name = 'freeze'
    usage = '%prog [OPTIONS]'
    summary = 'Output all currently installed packages (exact versions) to stdout'

    def __init__(self):
        super(FreezeCommand, self).__init__()
        self.output = []
        self.installations = {}
        
        self.parser.add_option(
            '-r', '--requirement',
            dest='requirement',
            action='store',
            default=None,
            metavar='FILENAME',
            help='Use the given requirements file as a hint about how to generate the new frozen requirements')

        self.parser.add_option(
            '-f', '--find-links',
            dest='find_links',
            action='append',
            default=[],
            metavar='URL',
            help='URL for finding packages, which will be added to the frozen requirements file')

        self.parser.add_option(
            '-l', '--local',
            dest='local',
            action='store_true',
            default=False,
            help='If in a virtualenv, do not report globally-installed packages')

        self.parser.add_option(
            '-s', '--skip-regex',
            dest='skip_requirements_regex',
            action='store',
            default=None,
            metavar='REGEX',
            help='Requirements matching regex will be filtered from output when using a requirement file')

        self.parser.add_option(
            '-t', '--find-tags',
            dest='find_tags',
            action='store_true',
            default=False,
            help='Find tags')
        
        self.parser.add_option(
            '', '--output-format',
            dest='output_format',
            action='store',
            default='reqfile',
            metavar='FORMAT',
            help='Format for output (reqfile, json)')
        
        self.parser.add_option(
            '-d', '--default_vcs',
            dest='default_vcs',
            action='store',
            default=None,
            metavar='VCS',            
            help='Default vcs to use: [svn, git, bzr, hg]')

    def setup_logging(self):
        logger.move_stdout_to_stderr()

    def write(self, data):
        if isinstance(data, basestring):
            return self.output.append(data)
        return self.output.extend(data)

    def write_json(self, handle, indent=2):
        """
        writes a json formatter, ignores most extra reqfile options or
        positional information

        Sorted output only supported for 2.7 or better.
        """
        if sys.version_info.major >= 2 and sys.version_info.minor >= 7:
            from collections import OrderedDict as dict_class
        else:
            dict_class = dict

        outdata = dict_class(find_links=[],
                             editable=[],
                             indexes=[],
                             requirements=dict_class())
        
        flag_keys = {'-f':'find_links',
                     '-i':'indexes',
                     '-e':'editable'}

        FLAG = re.compile(r'^(?P<flag>\-e|\-f|\-i)\s+(?P<url>.*)$' )
        for line in sorted(self.output):
            if line.startswith('#'):
                continue
            
            elif line.startswith('-'):
                match = FLAG.match(line)
                data = match.groupdict()
                if match:
                    key = flag_keys[data['flag']]
                    outdata[key].append(data['url'])

            elif not line.startswith('-'):
                pkg, version = line.split('==')
                outdata['requirements'][pkg] = version.strip()
              
        json.dump(outdata, handle, indent=indent)
        handle.write('\n')

    def write_reqfile(self, handle):
        for line in self.output:
            handle.write(line)

    def write_output(self, handle=None, format=None):
        writer = getattr(self, 'write_%s' %format, None)
        if writer:
            if handle is None:
                handle = sys.stdout
            return writer(handle)

    def dependency_links(self, find_links=[]):
        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    yield link
                    
        for link in find_links:
            if '#egg=' in link:
                yield link
                
    def write_requirement(self, requirement, skip_regex=None, default_vcs='git'):
        if skip_regex:
            skip_match = re.compile(skip_regex)
        req_f = open(requirement)
        for line in req_f:
            if not line.strip() or line.strip().startswith('#'):
                yield line
                continue
            if skip_match and skip_match.search(line):
                yield line
                continue
            elif line.startswith('-e') or line.startswith('--editable'):
                if line.startswith('-e'):
                    line = line[2:].strip()
                else:
                    line = line[len('--editable'):].strip().lstrip('=')
                line_req = InstallRequirement.from_editable(line, default_vcs=default_vcs)
            elif (line.startswith('-r') or line.startswith('--requirement')
                  or line.startswith('-Z') or line.startswith('--always-unzip')
                  or line.startswith('-f') or line.startswith('-i')
                  or line.startswith('--extra-index-url')):
                yield line
                continue
            else:
                line_req = InstallRequirement.from_line(line)
            if not line_req.name:
                logger.notify("Skipping line because it's not clear what it would install: %s"
                              % line.strip())
                logger.notify("  (add #egg=PackageName to the URL to avoid this warning)")
                continue
            if line_req.name not in self.installations:
                logger.warn("Requirement file contains %s, but that package is not installed"
                            % line.strip())
                continue
            yield str(self.installations[line_req.name])
            del self.installations[line_req.name]

    def run(self, options, args):
        requirement = options.requirement
        find_links = options.find_links or []
        local_only = options.local

        write = self.write

        dependency_links = list(self.dependency_links(find_links))
        write("-f %s\n" %link for link in dependency_links)

        for dist in get_installed_distributions(local_only=local_only):
            req = pip.FrozenRequirement.from_dist(dist, dependency_links, find_tags=options.find_tags)
            self.installations[req.name] = req

        if requirement:
            write(self.requirement_lines(requirement, options.skip_requirements_regex, options.default_vcs))
            write('## The following requirements were added by pip --freeze:\n')

        for installation in sorted(self.installations.values(), key=lambda x: x.name):
            write(str(installation))
            
        return self.write_output(format=options.output_format)


FreezeCommand()
