"""Handles all Cloud Storage support"""

import logging
import os
import typing
import urllib.parse
from typing import Dict, Iterator, List, Optional, Tuple, Type

from pip._internal.models.link import Link
from pip._internal.network.download import Downloader
from pip._internal.utils.filetypes import is_archive_file, is_wheel_file
from pip._internal.utils.misc import rmtree
from pip._internal.utils.subprocess import WithSubprocess

__all__ = ["cloudstorage"]


logger = logging.getLogger(__name__)


class InvalidCloudProviderObjectURL(Exception):
    pass


class CloudStorageObjectRef:
    @staticmethod
    def get_bucket(url: str) -> str:
        """
        Extract the bucket file from a cloud storage object URL
        """
        bucket = urllib.parse.urlsplit(urllib.parse.unquote(url)).hostname
        if not bucket:
            raise InvalidCloudProviderObjectURL(
                "Unable to extrack bucket name from URL: {}".format(url)
            )
        return bucket

    @staticmethod
    def get_object_path(url: str) -> str:
        """
        Extract the object path from a cloud storage object URL
        """
        return urllib.parse.urlsplit(urllib.parse.unquote(url)).path.lstrip("/")

    @staticmethod
    def get_scheme(url: str) -> str:
        """
        Extract the scheme from a cloud storage object URL
        """
        return urllib.parse.urlsplit(urllib.parse.unquote(url)).scheme

    @classmethod
    def from_link(cls, link: Link):
        """
        Construct a cloud storage object ref from a `Link` object
        """
        return CloudStorageObjectRef(
            scheme=cls.get_scheme(link.url),
            bucket=cls.get_bucket(link.url),
            path=cls.get_object_path(link.url),
        )

    scheme: str
    bucket: str
    path: str

    def __init__(self, scheme, bucket, path):
        """
        Construct a cloud storage object ref
        """
        self.scheme = scheme
        self.bucket = bucket
        self.path = path

    def __str__(self) -> str:
        return "{}://{}/{}".format(self.scheme, self.bucket, self.path)

    def get_target(self) -> str:
        """
        Extract the target file from a cloud storage object ref
        """
        for s in reversed(self.path.split("/")):
            if s != "":
                return s

        raise InvalidCloudProviderObjectURL(
            "Unable to parse target from Cloud Storage object URL: {}".format(self)
        )


class CloudStorageSupport:
    _registry: Dict[str, "CloudStorageProvider"] = {}
    schemes = ["gs", "s3"]

    def __init__(self) -> None:
        # Register more schemes with urlparse for various version control
        # systems
        urllib.parse.uses_netloc.extend(self.schemes)
        super().__init__()

    def __iter__(self) -> Iterator[str]:
        return self._registry.__iter__()

    @property
    def downloaders(self) -> List["Downloader"]:
        return list(self._registry.values())

    def register(self, cls: Type["CloudStorageProvider"]) -> None:
        if not hasattr(cls, "name"):
            logger.warning("Cannot register Cloud Storage Provider %s", cls.__name__)
            return
        if cls.name not in self._registry:
            self._registry[cls.name] = cls()
            logger.debug("Registered Cloud Storage Provider backend: %s", cls.name)

    def unregister(self, name: str) -> None:
        if name in self._registry:
            del self._registry[name]


cloudstorage = CloudStorageSupport()


class CloudStorageProvider(WithSubprocess, Downloader):
    name: str
    cli: typing.Tuple[str, ...] = ()
    scheme: str = ""
    subprocess_cmd: Optional[Tuple[str, ...]]

    @staticmethod
    def is_package_file(ref: CloudStorageObjectRef) -> bool:
        """
        Return True if the target of a cloud storage object URL is a valid package file

        :param ref: the ref of the object to being downloaded
        :return: True if the ref's target is a package file
        """
        target = ref.get_target()
        return is_archive_file(target) or is_wheel_file(target)

    def download(self, ref: CloudStorageObjectRef, dest: str) -> None:
        raise NotImplementedError()

    def is_supported(self, link: Link) -> bool:
        return link.scheme.lower() == self.scheme.lower()

    def __call__(self, link: Link, location: str) -> Tuple[str, Optional[str]]:
        """
        Ensure the package referenced by link is downloaded and
        stored in the location provided

        :param link: the link to the referenced package
        :param location: the location to store the package in
        :return: the target of the URL (could be file or directory)
        """
        ref = CloudStorageObjectRef.from_link(link)
        target = ref.get_target()
        if os.path.exists(location):
            rmtree(location)
        dest = os.path.join(location, target)
        self.download(ref, dest)
        return dest, None
