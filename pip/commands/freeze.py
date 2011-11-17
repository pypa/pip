import json
import sys
from pip.basecommand import Command
from pip.data import FreezeData
from pip.log import logger


class FreezeCommand(Command):
    name = 'freeze'
    usage = '%prog [OPTIONS]'
    summary = 'Output all currently installed packages (exact versions) to stdout'
    data_class = FreezeData
    default_format = 'reqfile'
    
    def __init__(self):
        super(FreezeCommand, self).__init__()
        
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

    def write_json(self, data, handle, indent=2):
        """
        writes a json formatter, ignores most extra reqfile options or
        positional information

        Sorted output only supported for 2.7 or better.
        """
        json.dump(data.as_dict, handle, indent=indent)
        handle.write('\n')

    def write_reqfile(self, data, handle):
        for line in data:  
            handle.write(line)

    def write_output(self, data, handle, format=None):
        writer = getattr(self, 'write_%s' %format, None)
        if writer:
            return writer(data, handle)

    def run(self, options, args):
        requirement = options.requirement
        find_links = options.find_links or []
        local_only = options.local
        find_tags = options.find_tags
        skip_requirements_regex = options.skip_requirements_regex
        default_vcs = options.default_vcs
        output_format = options.output_format
        write_on_load = output_format == 'reqfile'
        handle = sys.stdout
        data = self.data_class.load_all(local_only, find_links, requirement, find_tags,
                                        skip_requirements_regex,
                                        default_vcs, write_on_load, handle=handle, logger=logger)
        if output_format != 'reqfile':
            return self.write_output(data, handle, format=output_format)

FreezeCommand()
