import logging

from pip._internal.cloudstorage.cloudstorage import (
    CloudStorageObjectRef,
    CloudStorageProvider,
    cloudstorage,
)
from pip._internal.utils.misc import display_path
from pip._internal.utils.subprocess import make_command

logger = logging.getLogger(__name__)


class GCPStorage(CloudStorageProvider):
    name = "gcp"
    subprocess_cmd = ("gsutil",)
    scheme = "gs"

    def verify_gsutil_cli(self) -> None:
        self.run_command(["version"], show_stdout=False, stdout_only=True)

    def download(self, ref: CloudStorageObjectRef, dest: str) -> None:
        logger.info("Downloading (with aws s3) %s to %s", ref, display_path(dest))
        self.verify_gsutil_cli()
        self.run_command(make_command("cp", str(ref), dest))


cloudstorage.register(GCPStorage)
