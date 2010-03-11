import os
import shutil
import tempfile
import re
from pip import call_subprocess
from pip.util import display_path
from pip.vcs import vcs, VersionControl
from pip.log import logger

class Git(VersionControl):
    name = 'git'
    dirname = '.git'
    repo_name = 'clone'
    schemes = ('git', 'git+http', 'git+ssh', 'git+git')
    bundle_file = 'git-clone.txt'
    guide = ('# This was a Git repo; to make it a repo again run:\n'
        'git init\ngit remote add origin %(url)s -f\ngit checkout %(rev)s\n')

    def parse_vcs_bundle_file(self, content):
        url = rev = None
        for line in content.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue
            url_match = re.search(r'git\s*remote\s*add\s*origin(.*)\s*-f', line)
            if url_match:
                url = url_match.group(1).strip()
            rev_match = re.search(r'^git\s*checkout\s*-q\s*(.*)\s*', line)
            if rev_match:
                rev = rev_match.group(1).strip()
            if url and rev:
                return url, rev
        return None, None

    def unpack(self, location):
        """Clone the Git repository at the url to the destination location"""
        url, rev = self.get_url_rev()
        logger.notify('Cloning Git repository %s to %s' % (url, location))
        logger.indent += 2
        try:
            if os.path.exists(location):
                os.rmdir(location)
            call_subprocess(
                [self.cmd, 'clone', url, location],
                filter_stdout=self._filter, show_stdout=False)
        finally:
            logger.indent -= 2

    def export(self, location):
        """Export the Git repository at the url to the destination location"""
        temp_dir = tempfile.mkdtemp('-export', 'pip-')
        self.unpack(temp_dir)
        try:
            if not location.endswith('/'):
                location = location + '/'
            call_subprocess(
                [self.cmd, 'checkout-index', '-a', '-f', '--prefix', location],
                filter_stdout=self._filter, show_stdout=False, cwd=temp_dir)
        finally:
            shutil.rmtree(temp_dir)

    def check_rev_options(self, rev, dest, rev_options):
        """Check the revision options before checkout to compensate that tags
        and branches may need origin/ as a prefix"""
        if rev is None:
            # bail and use preset
            return rev_options
        revisions = self.get_tag_revs(dest)
        revisions.update(self.get_branch_revs(dest))
        if rev in revisions:
            # if rev is a sha
            return [rev]
        inverse_revisions = dict((v,k) for k, v in revisions.iteritems())
        if rev not in inverse_revisions: # is rev a name or tag?
            origin_rev = 'origin/%s' % rev
            if origin_rev in inverse_revisions:
                rev = inverse_revisions[origin_rev]
            else:
                logger.warn("Could not find a tag or branch '%s', assuming commit." % rev)
        return [rev]

    def switch(self, dest, url, rev_options):
        call_subprocess(
            [self.cmd, 'config', 'remote.origin.url', url], cwd=dest)
        call_subprocess(
            [self.cmd, 'checkout', '-q'] + rev_options, cwd=dest)

    def update(self, dest, rev_options):
        call_subprocess([self.cmd, 'fetch', '-q'], cwd=dest)
        call_subprocess(
            [self.cmd, 'checkout', '-q', '-f'] + rev_options, cwd=dest)

    def obtain(self, dest):
        url, rev = self.get_url_rev()
        if rev:
            rev_options = [rev]
            rev_display = ' (to %s)' % rev
        else:
            rev_options = ['master']
            rev_display = ''
        if self.check_destination(dest, url, rev_options, rev_display):
            logger.notify('Cloning %s%s to %s' % (url, rev_display, display_path(dest)))
            call_subprocess([self.cmd, 'clone', '-q', url, dest])
            checked_rev = self.check_rev_options(rev, dest, rev_options)
            # only explicitely checkout the "revision" in case the check
            # found a valid tag, commit or branch
            if rev_options != checked_rev:
                call_subprocess(
                    [self.cmd, 'checkout', '-q'] + checked_rev, cwd=dest)

    def get_url(self, location):
        url = call_subprocess(
            [self.cmd, 'config', 'remote.origin.url'],
            show_stdout=False, cwd=location)
        return url.strip()

    def get_revision(self, location):
        current_rev = call_subprocess(
            [self.cmd, 'rev-parse', 'HEAD'], show_stdout=False, cwd=location)
        return current_rev.strip()

    def get_tag_revs(self, location):
        tags = call_subprocess(
            [self.cmd, 'tag', '-l'],
            show_stdout=False, raise_on_returncode=False, cwd=location)
        tag_revs = []
        for line in tags.splitlines():
            tag = line.strip()
            rev = call_subprocess(
                [self.cmd, 'rev-parse', tag], show_stdout=False, cwd=location)
            tag_revs.append((rev.strip(), tag))
        tag_revs = dict(tag_revs)
        return tag_revs

    def get_branch_revs(self, location):
        branches = call_subprocess(
            [self.cmd, 'branch', '-r'], show_stdout=False, cwd=location)
        branch_revs = []
        for line in branches.splitlines():
            line = line.split('->')[0].strip()
            branch = "".join([b for b in line.split() if b != '*'])
            rev = call_subprocess(
                [self.cmd, 'rev-parse', branch], show_stdout=False, cwd=location)
            branch_revs.append((rev.strip(), branch))
        branch_revs = dict(branch_revs)
        return branch_revs

    def get_src_requirement(self, dist, location, find_tags):
        repo = self.get_url(location)
        if not repo.lower().startswith('git:'):
            repo = 'git+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        if not repo:
            return None
        current_rev = self.get_revision(location)
        tag_revs = self.get_tag_revs(location)
        branch_revs = self.get_branch_revs(location)

        if current_rev in tag_revs:
            # It's a tag
            full_egg_name = '%s-%s' % (egg_project_name, tag_revs[current_rev])
        elif (current_rev in branch_revs and
              branch_revs[current_rev] != 'origin/master'):
            # It's the head of a branch
            full_egg_name = '%s-%s' % (dist.egg_name(),
                                       branch_revs[current_rev].replace('origin/', ''))
        else:
            full_egg_name = '%s-dev' % dist.egg_name()

        return '%s@%s#egg=%s' % (repo, current_rev, full_egg_name)

    def get_url_rev(self):
        """
        Prefixes stub URLs like 'user@hostname:user/repo.git' with 'ssh://'.
        That's required because although they use SSH they sometimes doesn't
        work with a ssh:// scheme (e.g. Github). But we need a scheme for
        parsing. Hence we remove it again afterwards and return it as a stub.
        """
        if not '://' in self.url:
            self.url = self.url.replace('git+', 'git+ssh://')
            url, rev = super(Git, self).get_url_rev()
            url = url.replace('ssh://', '')
            return url, rev
        return super(Git, self).get_url_rev()

vcs.register(Git)
