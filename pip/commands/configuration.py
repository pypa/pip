import logging
import os
import subprocess

from pip.basecommand import Command
from pip.configuration import Configuration
from pip.exceptions import PipError
from pip.locations import venv_config_file
from pip.status_codes import SUCCESS, ERROR

logger = logging.getLogger(__name__)


class ConfigurationCommand(Command):
    """Manage local and global configuration."""
    name = 'config'
    usage = """
        %prog [<file-option>] list
        %prog [<file-option>] [--editor <editor-path>] edit

        %prog [<file-option>] get name
        %prog [<file-option>] set name value
        %prog [<file-option>] unset name
    """

    summary = """
        Manage local and global configuration.

        Subcommands:

        list: List the active configuration (or from the file specified)
        edit: Edit the configuration file in an editor
        get: Get the value associated with name
        set: Set the name=value
        unset: Unset the value associated with name

        If none of --user, --global and --venv are passed, a virtual
        environment configuration file is used if one is active and the file
        exists. Otherwise, all modifications happen on the to the user file by
        default.
    """

    def __init__(self, *args, **kwargs):
        super(ConfigurationCommand, self).__init__(*args, **kwargs)

        self.configuration = None

        self.cmd_opts.add_option(
            '--editor',
            dest='editor',
            action='store',
            default=None,
            help=(
                'Editor to use to edit the file. Uses '
                '$EDITOR if not passed.'
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
        handlers = {
            "list": self.list_values,
            "edit": self.open_in_editor,
            "get": self.get_name,
            "set": self.set_name_value,
            "unset": self.unset_name
        }

        # Determine action
        if not args or args[0] not in handlers:
            logger.error("Need an action ({}) to perform.".format(
                ", ".join(sorted(handlers)))
            )
            return ERROR

        action = args[0]

        # Determine which configuration files are to be loaded
        #    Depends on whether the command is modifying.
        try:
            load_only = self._determine_file(
                options, need_value=(action in ["get", "set", "unset"])
            )
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        # Load a new configuration
        isolated = options.isolated_mode
        self.configuration = Configuration(
            isolated=isolated, load_only=load_only
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

    def _determine_file(self, options, need_value):
        file_options = {
            "user": options.user_file,
            "site-wide": options.global_file,
            "venv": options.venv_file
        }

        if sum(file_options.values()) == 0:
            if not need_value:
                return None
            # Default to user, unless there's a virtualenv file.
            elif os.path.exists(venv_config_file):
                return "venv"
            else:
                return "user"
        elif sum(file_options.values()) == 1:
            # There's probably a better expression for this.
            return [key for key in file_options if file_options[key]][0]

        raise PipError(
            "Need exactly one file to operate upon "
            "(--user, --venv, --global) to perform."
        )


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
