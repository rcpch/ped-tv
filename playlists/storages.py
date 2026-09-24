import os

from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage


class AttachmentS3Storage(S3Boto3Storage):
    """S3-compatible storage that serves files as downloads, not inline."""

    def get_object_parameters(self, name):
        params = super().get_object_parameters(name)
        params.setdefault(
            "ContentDisposition", f'attachment; filename="{os.path.basename(name)}"'
        )
        return params


class AttachmentAzureStorage(AzureStorage):
    """Azure Blob storage that serves files as downloads, not inline."""

    def get_object_parameters(self, name):
        params = super().get_object_parameters(name)
        params.setdefault(
            "content_disposition", f'attachment; filename="{os.path.basename(name)}"'
        )
        return params


def attachment_storage():
    """Build a storage matching the configured default backend, but with
    Content-Disposition: attachment on every uploaded object.

    Used for pressed playlist MP4s so browsers show a save dialog instead
    of playing the file inline — the anchor `download` attribute is ignored
    for the cross-origin object-storage URLs.
    """
    config = settings.STORAGES["default"]
    options = config.get("OPTIONS", {})
    if "azure" in config["BACKEND"]:
        return AttachmentAzureStorage(**options)
    return AttachmentS3Storage(**options)