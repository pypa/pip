import os

from pip._vendor.pkg_resources import DistInfoDistribution

from pip._internal.distributions.base import AbstractDistribution
from pip._internal.network.shallow.httpfile import Context as HttpContext
from pip._internal.network.shallow.httpfile import Url
from pip._internal.network.shallow.wheel import Context as WheelContext
from pip._internal.network.shallow.wheel import (
    ProjectName,
    WheelMetadataRequest,
)
from pip._internal.network.shallow.zipfile import Context as ZipContext
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.wheel import WheelMetadata

if MYPY_CHECK_RUNNING:
    from typing import Any
    from pip._vendor.pkg_resources import Distribution
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.models.link import Link
    from pip._internal.network.download import Downloader
    from pip._internal.req import InstallRequirement


class DistributionNeedingFinalHydration(DistInfoDistribution):
    def __init__(self, link, downloader, download_dir, *args, **kwargs):
        # type: (Link, Downloader, str, Any, Any) -> None
        super(DistributionNeedingFinalHydration, self).__init__(
            *args, **kwargs)
        self.final_link = link
        self.downloader = downloader
        self.download_dir = download_dir

    def finally_hydrate(self):
        # type: () -> None
        download = self.downloader(self.final_link)
        output_filename = os.path.join(self.download_dir, download.filename)
        with open(output_filename, 'wb') as f:
            for chunk in download.chunks:
                f.write(chunk)


class ShallowWheelDistribution(AbstractDistribution):
    """Represents a wheel distribution.

    This does not need any preparation as wheels can be directly unpacked.
    """

    def __init__(self, req, downloader, download_dir):
        # type: (InstallRequirement, Downloader, str) -> None
        super(ShallowWheelDistribution, self).__init__(req)
        self._downloader = downloader
        self._download_dir = download_dir

    @property
    def _wheel_context(self):
        # type: () -> WheelContext
        http_ctx = HttpContext(self._downloader.get_session())
        zip_ctx = ZipContext(http_ctx)
        wheel_ctx = WheelContext(zip_ctx)
        return wheel_ctx

    def get_pkg_resources_distribution(self):
        # type: () -> Distribution
        """Loads the metadata from the shallow wheel file into memory and
        returns a Distribution that uses it, not relying on the wheel file or
        requirement.
        """
        # Wheels are never unnamed.
        assert self.req.name
        assert self.req.link

        project_name = ProjectName(self.req.name)
        remote_location = Url(self.req.link.url)

        wheel_req = WheelMetadataRequest(
            url=remote_location,
            project_name=project_name,
        )
        metadata = (self
                    ._wheel_context
                    .extract_wheel_metadata(wheel_req)
                    .contents)

        wheel_filename = self.req.link.filename
        wheel_metadata = WheelMetadata({'METADATA': metadata}, wheel_filename)

        return DistributionNeedingFinalHydration(
            link=self.req.link,
            downloader=self._downloader,
            download_dir=self._download_dir,
            location=wheel_filename,
            metadata=wheel_metadata,
            project_name=project_name.name,
        )

    def prepare_distribution_metadata(self, finder, build_isolation):
        # type: (PackageFinder, bool) -> None
        pass
