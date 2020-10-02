""" TUF (TheUpdateFramework) integration
"""

import hashlib
import logging
import os.path
import os
import shutil

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.utils.temp_dir import TempDirectory
from pip._vendor.six.moves.urllib import parse as urllib_parse

# TODO vendor tuf
import tuf.client.updater
from tuf.exceptions import (
    NoWorkingMirrorError,
    RepositoryError,
    UnknownTargetError,
)
import tuf.settings


logger = logging.getLogger(__name__)


# TUF Updater abstraction for a specific Warehouse instance (index URL)
class SecureDownloader:
    # throws RepositoryError, ?
    def __init__(self, index_url, metadata_dir, cache_dir):
        # type: (str, str, Optional[str]) -> SecureDownloader
        # Construct unique directory name based on the url
        # TODO make sure this is robust
        dir_name = hashlib.sha224(index_url.encode('utf-8')).hexdigest()
        
        # we expect metadata and index files to be hosted on same netloc
        split_url = urllib_parse.urlsplit(index_url)
        base_url = urllib_parse.urlunsplit([split_url.scheme, split_url.netloc, '', '', ''])
        targets_path = split_url.path.lstrip('/')

        # Store two separate mirror configs to workaround https://github.com/theupdateframework/tuf/issues/1143
        # TODO: metadata_path should not be hard coded but solution is not decided yet
        self._index_mirrors = {
            base_url: {
                'url_prefix': base_url,
                'metadata_path': 'tuf/',
                'targets_path': targets_path,
                'confined_target_dirs': ['']
            }
        }
        self._distribution_mirrors = {
            # TODO: should remove targets_path when possible:
            # https://github.com/theupdateframework/tuf/issues/1079
            base_url: {
                'url_prefix': base_url,
                'metadata_path': 'tuf/',
                'targets_path': 'None', 
                'confined_target_dirs': []
            }
        }

        self._updater = tuf.client.updater.Updater(dir_name, self._index_mirrors)
        self._refreshed = False

        self._cache_dir = cache_dir


    def __str__(self):
        return str(self._updater)


    # Make sure we have refreshed metadata exactly once (we
    # want all downloads to be done from a consistent repository)
    # Raises NoWorkingMirrorError, ?
    def _ensure_fresh_metadata(self):
        if not self._refreshed:
            self._updater.refresh()
            self._refreshed = True


    # Ensure give mirror is in updater mirror config
    def _ensure_distribution_mirror_config(self, mirror_url):
        # metadata/index mirror config is known from the start, but 
        # the distribution mirror is only known after the index
        # files are read: make sure it's configured

        # TODO: split mirror_url into prefix and targets_path ?
        # This would allow using confined_target_dirs to prevent
        # index file requests being made to this mirror
        if mirror_url not in self._distribution_mirrors:
            self._distribution_mirrors[mirror_url] = {
                'url_prefix': mirror_url,
                'metadata_path': 'None', # TODO: Actual None does not work with current tuf 
                'targets_path': '',
                'confined_target_dirs': ['']
            }


    # split a distribution url into base path and target name:
    # "https://files.pythonhosted.org/packages/8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz#sha256=0e5034cf8046ba77c62e95a45d776d2c59998b26f181ceaf5cec516115e3f85a"
    #    ->
    # ("https://files.pythonhosted.org/packages/", "8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz")
    def _split_distribution_url(self, link):
        # type: (Link) -> (str, str)
        split_path = link.path.split('/')

        # sanity check: does path contain directory names that form blake2b hash
        blake2b = ''.join(split_path[-4:-1])
        if len(blake2b) != 64:
            raise ValueError('Expected structure not found in link "{}"'.format(link))

        # NOTE: knowledge of path structure is required to do the split here
        # target name is filename plus three directory levels to form full blake hash
        target_name = '/'.join(split_path[-4:])
        base_path = '/'.join(split_path[:-4])
        base_url = urllib_parse.urlunsplit([link.scheme, link.netloc, base_path, '', ''])
        return base_url, target_name


    # Download project index file, return file name
    # project name is e.g. 'django'. From pypi this will download
    # "https://pypi.org/simple/django"
    def download_index(self, project_name):
        try:
            self._ensure_fresh_metadata()

            self._updater.mirrors = self._index_mirrors

            # TODO warehouse setup for hashed index files is still undecided: this assumes /simple/{PROJECT}/{HASH}.index.html
            target_name = project_name + "/index.html"
            # fetch the targetinfo. If we don't have the correct target version already download it too
            target = self._updater.get_one_valid_targetinfo(target_name)
            if self._updater.updated_targets([target], self._cache_dir):
                self._updater.download_target(target, self._cache_dir)

            return os.path.join(self._cache_dir, target_name)
        except UnknownTargetError as e:
            logger.debug("Unknown %s", target_name)
            return None
        except NoWorkingMirrorError as e:
            logger.warning("Failed to download index for %s: %s", project_name, e)
            return None


    # Download a distribution file
    # Requires a link with url
    #   url is e.g. https://files.pythonhosted.org/packages/8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz#sha256=0e5034cf8046ba77c62e95a45d776d2c59998b26f181ceaf5cec516115e3f85a
    # Raises NetworkConnectionError, ?
    def download_distribution(self, link):
        # TODO maybe double check that comes_from matches our index_url
        try:
            self._ensure_fresh_metadata()

            base_url, target_name = self._split_distribution_url(link)
            self._ensure_distribution_mirror_config(base_url)
            self._updater.mirrors = self._distribution_mirrors

            # fetch the targetinfo. If we don't have the correct target version already download it too
            logger.debug("Getting TUF target_info for " + target_name)
            logname = target_name.split('/')[-1]
            target = self._updater.get_one_valid_targetinfo(target_name)

            if self._updater.updated_targets([target], self._cache_dir):
                logger.info("Downloading %s", logname)
                self._updater.download_target(target, self._cache_dir, prefix_filename_with_hash=False)
            else:
                logger.info("Using cached %s", logname)

            return os.path.join(self._cache_dir, target_name)

        except NoWorkingMirrorError as e:
            # This is close but not strictly speaking always true: there might
            # be other reasons for NoWorkingMirror than Network issues
            raise NetworkConnectionError(e)


# TODO could provide some extra
# functionality like downloader lookup based on distribution download Link (currently
# implemented in prepare.py:get_http_url()) or lookup that at least canonicalizes the URL
class SecureUpdateSession:
    def __init__(self, index_urls, metadata_dir, cache_dir):
        # type: (List[str], str, Optional[str]) -> SecureUpdateSession
        self._downloaders = {} # dictionary of index_uri:SecureDownloader

        self._bootstrap_metadata(metadata_dir)

        # global tuf settings
        # TODO: review settings: do we need to change anything else
        tuf.settings.repositories_directory = metadata_dir
        tuf.log.set_log_level(logging.ERROR)
    
        # Use a temporary directory if cache is not available
        if cache_dir is None:
            cache_dir = TempDirectory(globally_managed=True).path

        for index_url in index_urls:
            index_url = self._canonicalize_url(index_url)
            try:
                downloader = SecureDownloader(index_url, metadata_dir, cache_dir)
                self._downloaders[index_url] = downloader
            except RepositoryError as e:
                # No TUF Metadata was found for this index_url
                # TODO: check for actual metadata file existence:
                # https://github.com/theupdateframework/tuf/issues/1063
                logger.debug('Failed to find secure update metadata for "%s": %s', index_url, e)


    # TODO: better canonicalization
    @staticmethod
    def _canonicalize_url(url):
        return urllib_parse.urljoin(url + '/', '.')

    # Bootstrap the TUF metadata with metadata we ship with the code
    # (only if that TUF metadata does not exist yet).
    # Raises OSErrors like FileExistsError etc
    # TODO: handle failures better: e.g. if bootstrap fails somehow, remove the directory
    def _bootstrap_metadata(self, metadata_dir):
        # type: (str) -> None
        bootstrapdir = os.path.join(
            os.path.dirname(__file__),
            "secure_update_bootstrap"
        )

        for bootstrap in os.listdir(bootstrapdir):
            # check if metadata matching this name already exists
            dirname = os.path.join(metadata_dir, bootstrap)
            if os.path.exists(dirname):
                continue

            # create the structure TUF expects
            logger.debug("Bootstrapping TUF metadata for {}".format(bootstrap))
            os.makedirs(os.path.join(dirname, "metadata", "current"))
            os.mkdir(os.path.join(dirname, "metadata", "previous"))
            shutil.copyfile(
                os.path.join(bootstrapdir, bootstrap, "root.json"),
                os.path.join(dirname, "metadata", "current", "root.json")
            )


    def get_downloader(self, index_url):
        # type: (str) -> Optional[SecureDownloader]
        index_url = self._canonicalize_url(index_url)
        return self._downloaders.get(index_url)
