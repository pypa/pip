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

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args)
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

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

    def list_values(self, options, args):
        self._get_n_args(args, n=0)

        for key, value in sorted(self.configuration.items()):
            logger.info("%s=%r", key, value)

    def get_name(self, options, args):
        key = self._get_n_args(args, n=1)
        value = self.configuration.get_value(key)

        logger.info("%s", value)

    def set_name_value(self, options, args):
        key, value = self._get_n_args(args, n=2)
        self.configuration.set_value(key, value)

        self._save_configuration()

    def unset_name(self, options, args):
        key = self._get_n_args(args, n=1)
        self.configuration.unset_value(key)

        self._save_configuration()

    def open_in_editor(self, options, args):
        editor = self._determine_editor(options)

        file_ = self.configuration.get_file()
        if file_ is None:
            raise PipError("Could not determine appropriate file.")

        try:
            subprocess.check_call([editor, file_])
        except subprocess.CalledProcessError as e:
            raise PipError(
                "Editor Subprocess exited with exit code {}"
                .format(e.returncode)
            )

    def _get_n_args(self, args, n):
        if len(args[1:]) != n:
            raise PipError(
                "Got unexpected number of arguments, expected {}.".format(n)
            )

        if n == 1:
            return args[1]
        else:
            return args[1:]

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
            raise PipError("Internal Error.")

    def _determine_editor(self, options):
        if options.editor is not None:
            return options.editor
        elif "EDITOR" in os.environ:
            return os.environ["EDITOR"]
        else:
            raise PipError("Could not determine editor to use.")
