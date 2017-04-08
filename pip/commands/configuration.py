import logging
import subprocess

from pip.basecommand import Command
from pip.configuration import Configuration
from pip.exceptions import ConfigurationError
from pip.status_codes import SUCCESS, ERROR

logger = logging.getLogger(__name__)


class ConfigurationCommand(Command):
    """Manage local and global configuration."""
    name = 'config'
    usage = """
        %prog [<file-option>] --list
        %prog [<file-option>] --edit --editor

        %prog [<file-option>] --get name
        %prog [<file-option>] --set name=value
        %prog [<file-option>] --unset name"""

    summary = 'Manage local and global configuration.'

    def __init__(self, *args, **kwargs):
        super(ConfigurationCommand, self).__init__(*args, **kwargs)

        self.configuration = None
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
            help='Use the system-wide configuration file only'
        )

        self.cmd_opts.add_option(
            '--user',
            dest='user_file',
            action='store_true',
            default=False,
            help='Use the user configuration file only'
        )

        self.cmd_opts.add_option(
            '--venv',
            dest='venv_file',
            action='store_true',
            default=False,
            help='Use the virtualenv configuration file only'
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options, args):

        # Determine what action is to be taken
        action_options = {
            "list": options.list,
            "edit": options.edit,
            "get": options.get_name,
            "set": options.set_name_value,
            "unset": options.unset_name,
        }

        action = None
        for k, v in action_options.items():
            if v:
                if action is not None:
                    # this works because of the conditional immediately after
                    # the loop.
                    action = None
                    break
                action = k

        if action is None:
            logger.error(
                "Need exactly one action (--list, --edit, "
                "--get, --set, --unset) to perform."
            )
            return ERROR

        # Determine which configuration files are to be loaded
        if sum([options.user_file, options.global_file, options.venv_file]):
            logger.error(
                "Need at-most one configuration file to use - pass "
                "only one of --global, --user, --venv."
            )
            return ERROR

        kwargs = {}
        if options.user_file:
            kwargs["load_only"] = "user"
        elif options.global_file:
            kwargs["load_only"] = "site-wide"
        elif options.venv_file:
            kwargs["load_only"] = "venv"
        elif action in ["set", "unset", "edit"]:
            logger.error(
                "Need one configuration file to modify - pass one of "
                "--global, --user, --venv."
            )
            return ERROR

        # Load a new configuration
        self.configuration = Configuration(
            isolated=options.isolated_mode, **kwargs
        )
        self.configuration.load()

        # Call the handler for the action with the options
        handlers = {
            "list": self.list_values,
            "edit": self.open_in_editor,
            "get": self.get_name,
            "set": self.set_name_value,
            "unset": self.unset_name
        }

        return handlers[action](options)

    def list_values(self, options):
        for key, value in sorted(self.configuration.items()):
            logger.info("%s=%r", key, value)
        return SUCCESS

    def open_in_editor(self, options):
        if options.editor is None:
            logger.error(
                "--edit requires an editor to be passed, either using "
                "--editor or by setting it in a configuration file."
            )
            return ERROR

        file = self.configuration.get_file()
        if file is None:
            logger.error(
                "Could not determine appropriate file."
            )
            return ERROR

        try:
            subprocess.check_call([options.editor, file])
        except subprocess.CalledProcessError as e:
            logger.error(
                "Subprocess exited with exit code %d", e.returncode
            )
            return ERROR
        else:
            return SUCCESS

    def get_name(self, options):
        try:
            value = self.configuration.get_value(options.get_name)
        except KeyError:
            logger.error("No key %r in configuration", options.get_name)
            return ERROR

        logger.info("%s", value)
        return SUCCESS

    def set_name_value(self, options):
        key, value = options.set_name_value.split("=", 1)

        try:
            self.configuration.set_value(key, value)
        except ConfigurationError:
            logger.error("Could not set value in configuration")
        else:
        return self._save_configuration()

    def unset_name(self, options):
        key = options.unset_name

        try:
            self.configuration.unset_value(key)
        except ConfigurationError:
            logger.error("Could not unset value in configuration")
        else:
        return self._save_configuration()

    def _save_configuration(self):
        # We successfully ran a modifying command. Need to save the
        # configuration.
        try:
            self.configuration.save()
        except Exception:
            logger.error(
                "Unable to save configuration. Please report this as a bug.",
                exc_info=1
            )
            return ERROR
        else:
            return SUCCESS
