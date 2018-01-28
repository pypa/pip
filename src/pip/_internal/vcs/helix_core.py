from __future__ import absolute_import

import logging
import os
import random
import re
import socket
import string

from pip._vendor.six.moves.urllib import parse as urllib_parse
from pip._internal.vcs import VersionControl, vcs

logger = logging.getLogger(__name__)

client_spec_template = """
Owner:   {user}
Host:    {host}
Client:  {name}
Root:    {client_path}
View:    /{server_path}/... //{name}/...
Options: allwrite rmdir
"""


def split_url(url, environ=os.environ):
    """
    Parses a URL and returns a 5-tuple of
    ``(port, depot_path, revision, username, password)``. Where fields are not
    present in the given URL, information from Helix Core environment variables
    (``P4PORT``, ``P4USER``, ``P4PASSWD``) is used.

    URL examples::

        ssl://me:p4ssw0rd@perforce1/depot/myproject
        p4://perforce1:1667/depot/myproject
        p4:///depot/myproject
    """

    if url.startswith("p4+"):
        url = url[3:]
    url = urllib_parse.urlsplit(url)

    p4path = url.path
    if '@' in p4path:
        p4path, p4rev = p4path.split("@")
    else:
        p4rev = None

    p4user = (
        url.username or
        environ.get("P4USER") or
        environ.get("USER") or
        environ.get("USERNAME") or
        '')
    p4passwd = (
        url.password or
        environ.get("P4PASSWD") or
        '')

    p4port = ["tcp", "perforce", "1666"]
    p4port_old = environ.get("P4PORT")
    if p4port_old:
        for i, v in enumerate(reversed(p4port_old.split(":"))):
            if v:
                p4port[-i - 1] = v
    if url.scheme != "p4":
        p4port[0] = url.scheme
    if url.hostname:
        p4port[1] = url.hostname
    if url.port:
        p4port[2] = str(url.port)
    p4port = ":".join(p4port)

    return p4port, p4path, p4rev, p4user, p4passwd


def join_url(p4port, p4path):
    """
    Return a Helix Core URL. Information that does not contribute to the
    uniqueness of the resource - i.e. username, password, protocol and
    revision - is not required by this function.
    """

    p4port = p4port or 'p4:'
    return urllib_parse.urlunsplit((
        'p4',
        p4port.split(":", 1)[1],
        p4path,
        '',
        ''))


class HelixCoreClient(object):
    """
    Represents a Helix Core client (a.k.a. workspace). Stores the local
    filesystem location of the client and a number of environment variables
    used by the ``p4`` executable to configure communication with the Helix
    Core server. These include:

    - ``P4CLIENT``: Name of the client.
    - ``P4PORT``: Protocol, hostname and port of the Helix Core server.
    - ``P4USER``
    - ``P4PASSWD``
    - ``P4PATH``: Depot path being mapped. This is a pip-specific extension
      that is unused by the ``p4`` executable.

    This class has methods for saving and loading the environment to a
    ``.p4pip/environ.txt`` file. The ``run()`` method can be used to execute
    a ``p4`` command within the client's environment.
    """

    def __init__(self, run_command, client_path, environ=None):
        self._run_command = run_command
        self.client_path = client_path
        self.environ = environ or {}
        self.p4pip_path = os.path.join(client_path, ".p4pip")
        self.environ_path = os.path.join(self.p4pip_path, "environ.txt")

        if environ is None:
            self.load_environ()

    def load_environ(self):
        """
        Load environment from ``.p4pip/environ.txt`` file.
        """

        self.environ.clear()

        with open(self.environ_path) as fd:
            for line in fd:
                name, value = line.strip().split("=", 2)
                self.environ[name] = value

    def save_environ(self):
        """
        Save environment to ``.p4pip/environ.txt`` file.
        """

        if not os.path.exists(self.p4pip_path):
            os.mkdir(self.p4pip_path)

        with open(self.environ_path, "w") as fd:
            for name, value in sorted(self.environ.items()):
                fd.write("%s=%s\n" % (name, value))

    def delete_environ(self):
        """
        Delete the ``.p4pip/environ.txt`` file.
        """

        os.remove(self.environ_path)
        os.rmdir(self.p4pip_path)

    def save(self):
        """
        Create or update the Helix Core client.
        """

        spec = client_spec_template.format(
            user=self.environ['P4USER'],
            host=socket.gethostname(),
            name=self.environ['P4CLIENT'],
            client_path=self.client_path,
            server_path=self.environ['P4PATH'])

        self.run('client', '-i', stdin=spec.encode('ascii'))

    def delete(self):
        """
        Delete the Helix Core client.
        """

        self.run('client', '-d', self.environ['P4CLIENT'])

    def run(self, *cmd, **kwargs):
        """
        Run a Helix Core command.
        """

        return self._run_command(
            cmd=list(cmd),
            cwd=self.client_path,
            extra_environ=self.environ,
            show_stdout=False,
            **kwargs)


class HelixCore(VersionControl):
    name = 'p4'
    dirname = '.p4pip'
    repo_name = 'workspace'
    schemes = (
        'p4+p4',
        'p4+tcp',
        'p4+tcp4',
        'p4+tcp6',
        'p4+tcp46',
        'p4+tcp64',
        'p4+ssl',
        'p4+ssl4',
        'p4+ssl6',
        'p4+ssl46',
        'p4+ssl64')

    def get_client(self, path, environ=None):
        return HelixCoreClient(self.run_command, path, environ)

    def get_base_rev_args(self, rev):
        return ['@%s' % rev]

    # Informational -----------------------------------------------------------

    def get_url(self, location):
        client = self.get_client(location)
        return join_url(client.environ['P4PORT'], client.environ['P4PATH'])

    def get_revision(self, location):
        client = self.get_client(location)
        havelist = re.findall(
            r"\.\.\. change (\d+)\n\.\.\. status have\n",
            client.run('cstat'))
        if havelist:
            return havelist[-1]
        else:
            return 0

    def is_commit_id_equal(self, dest, name):
        if not name:
            return False

        return self.get_revision(dest) == name

    def get_src_requirement(self, dist, location):
        return 'p4+%s@%s#egg=%s' % (
            self.get_url(location),
            self.get_revision(location),
            dist.egg_name().split('-', 1)[0])

    # Operations --------------------------------------------------------------

    def obtain(self, dest):
        p4port, p4path, p4rev, p4user, p4passwd = split_url(self.url)
        rev_options = self.make_rev_options(p4rev)
        url = join_url(p4port, p4path)

        environ = {
            'P4PORT': p4port,
            'P4PATH': p4path,
            'P4USER': p4user,
            'P4PASSWD': p4passwd,
            'P4CLIENT': 'pip-%s' % ''.join(
                random.choice(string.digits + string.ascii_lowercase)
                for _ in range(32))
        }

        if self.check_destination(dest, url, rev_options):
            logger.info('Syncing "%s"' % url)

            if not os.path.exists(dest):
                os.mkdir(dest)
            client = self.get_client(dest, environ)
            client.save_environ()
            client.save()
            client.run('sync', '-f', *rev_options.to_args())

    def update(self, dest, rev_options):
        client = self.get_client(dest)
        client.run('sync', '-f', *rev_options.to_args())

    def switch(self, dest, url, rev_options):
        p4port, p4path = split_url(url)[:2]
        client = self.get_client(dest)
        client.environ['P4PORT'] = p4port
        client.environ['P4PATH'] = p4path
        client.save_environ()
        client.save()
        client.run('sync', '-f', *rev_options.to_args())

    def export(self, location):
        self.obtain(location)
        client = self.get_client(location)
        client.delete()
        client.delete_environ()


vcs.register(HelixCore)
