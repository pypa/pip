import logging

from pip.basecommand import Command
from pip.configuration import Configuration
from pip.status_codes import SUCCESS, ERROR

logger = logging.getLogger(__name__)


class ConfigurationCommand(Command):
    """Manage local and global configuration."""
    name = 'config'
    usage = """
        %prog [<file-option>] --list
        %prog [<file-option>] --edit --editor <editor_path>

        %prog [<file-option>] --get <name>
        %prog [<file-option>] --set <name=value>
        %prog [<file-option>] --unset <name>"""

    summary = 'Manage local and global configuration.'

    def __init__(self, *args, **kwargs):
        super(ConfigurationCommand, self).__init__(*args, **kwargs)

        self.cmd_opts.add_option(
            '-l', '--list',
            dest='list',
            action='store_true',
            default=False,
            help='List the active configuration (or from the file specified)'
        )

        self.cmd_opts.add_option(
            '-e', '--edit',
            dest='edit',
            action='store_true',
            default=False,
            help='Edit the configuration file'
        )

        self.cmd_opts.add_option(
            '--get',
            dest='get_name',
            action='store',
            metavar='name',
            default=None,
            help='Get the value associated with name in the configuration file'
        )

        self.cmd_opts.add_option(
            '--set',
            dest='set_name_value',
            action='store',
            metavar='name=value',
            type="string",  # this is validated elsewhere
            default=None,
            help='Set name=value in the configuration file'
        )

        self.cmd_opts.add_option(
            '--unset',
            dest='unset_name',
            action='store',
            metavar='name',
            default=None,
            help=(
                'Unset the value associated with name in the configuration '
                'file'
            )
        )

        self.cmd_opts.add_option(
            '--global',
            dest='global_file',
            action='store_true',
            default=False,
            help='Use the global configuration file'
        )

        self.cmd_opts.add_option(
            '--virtualenv',
            dest='virtualenv_file',
            action='store_true',
            default=False,
            help='Use the virtualenv configuration file'
        )

        self.cmd_opts.add_option(
            '--user',
            dest='local_file',
            action='store_true',
            default=False,
            help='Use the user configuration file'
        )

        self.cmd_opts.add_option(
            '--editor',
            dest='editor',
            action='store',
            default=None,
            help='Editor to use to open configuration file'
        )

        self.parser.insert_option_group(0, self.cmd_opts)

        self.config = None

    # TODO: Warn of environment variable has overriden something.

    def run(self, options, args):
        # Will only do one thing at a time.
        actions_passed = list(map(bool, [
            options.list, options.edit, options.get_name,
            options.set_name_value, options.unset_name
        ]))

        if sum(actions_passed) != 1:
            logger.warning(
                "ERROR: Please provide only one of "
                "--list, --edit, --get, --set, --unset."
            )
            return ERROR

        # Get a nice string - 'action' is what has to be done.
        actions = ["list", "edit", "get", "set", "unset"]
        action = actions[actions_passed.index(True)]

        # Load the configuration
        # TODO: Implement these.
        if options.global_file:
            kwargs = {"global_only": True}
        elif options.virtualenv_file:
            kwargs = {"venv_only": True}
        elif options.local_file:
            kwargs = {"local_only": True}
        else:
            kwargs = {}

        self.config = Configuration(isolated=options.isolated, **kwargs)
        self.config.load()

        # Take the required action
        if action == "edit":
            return self.open_config_file_in_editor(options.editor)
        elif action == "list":
            return self.list_active_config()
        elif action == "get":
            return self.get_config_value(key)
        elif action == "set":
            key, value = options.set_name_value.split("=", 1)
            return self.set_config_value(key, value)
        elif action == "unset":
            return self.unset_config_value(key)
        else:
            raise Exception("pip and Python are broken. Report this issue.")

    # Actual functionality follows.
    # The following functions implement the "actions" and return the status
    # code of the command.

    def open_config_in_editor(self, editor):
        if editor is None:
            logger.warning(
                "ERROR: Please provide an executable file through "
                "--editor or set it."
            )
            return ERROR

        try:
            ...
        except OSError:
            logger.warning("ERROR: Could not open editor specified.")
            return ERROR

        return SUCCESS

    def list_active_config(self):
        for key, value in self.config.items():
            logger.info("%s=%s", key, value)
        return SUCCESS

    def get_config_value(self, key):
        if key in self.config.dictionary["env"]:
            logger.warning(
                "WARNING: There is an environment override for  %r.", key
            )

        try:
            value = self.config.get(key)
        except KeyError:
            logger.warning("ERROR: No key with name %r set.", key)
            return ERROR
        else:
            logger.info("%s", value)
            return SUCCESS

    def set_config_value(self, key, value):
        ...

    def unset_config_value(self, key):
        ...
