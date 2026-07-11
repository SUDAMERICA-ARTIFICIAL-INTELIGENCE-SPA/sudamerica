"""Google Cloud Storage utility for media uploads/downloads.

Handles:
- Upload binary data or files to GCS
- Generate signed URLs for time-limited access (works on Cloud Run)
- Download blobs by path

Auth: Uses Application Default Credentials (ADC).
- On Cloud Run: automatic via service account (uses IAM signBlob for signed URLs)
- Locally: `gcloud auth application-default login`
"""

import logging
import uuid
from datetime import timedelta
from pathlib import PurePosixPath

import google.auth
from google.auth.transport import requests as auth_requests
from google.cloud import storage as gcs

logger = logging.getLogger(__name__)

_client: gcs.Client | None = None
_signing_credentials = None


def _get_client() -> gcs.Client:
    global _client
    if _client is None:
        _client = gcs.Client()
    return _client


def _get_signing_credentials():
    """Get credentials capable of signing (works on Cloud Run via IAM signBlob)."""
    global _signing_credentials
    if _signing_credentials is not None:
        return _signing_credentials

    credentials, project = google.auth.default()

    # On Cloud Run, credentials are Compute Engine credentials which can't sign.
    # Wrap them in IAM-based signing credentials.
    if hasattr(credentials, "service_account_email"):
        from google.auth import iam
        from google.auth.transport import requests as auth_requests

        signer = iam.Signer(
            request=auth_requests.Request(),
            credentials=credentials,
            service_account_email=credentials.service_account_email,
        )

        from google.oauth2 import service_account
        _signing_credentials = service_account.IDTokenCredentials(
            signer=signer,
            service_account_email=credentials.service_account_email,
            token_uri="https://oauth2.googleapis.com/token",
            target_audience="",
        )
        return _signing_credentials

    # Locally with a service account key file, credentials can sign directly
    _signing_credentials = credentials
    return _signing_credentials


def upload_bytes(
    bucket_name: str,
    data: bytes,
    destination_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload raw bytes to GCS. Returns the blob path (not a URL)."""
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(data, content_type=content_type)
    logger.info("Uploaded %d bytes to gs://%s/%s", len(data), bucket_name, destination_path)
    return destination_path


def generate_signed_url(
    bucket_name: str,
    blob_path: str,
    expiration_hours: int = 168,
) -> str:
    """Generate a signed URL for a GCS object (default: 7 days).

    On Cloud Run, uses the service account's IAM signBlob capability.
    Locally, uses the credentials directly if they have a private key.
    """
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    try:
        # Try direct signing first (works with service account key files)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=expiration_hours),
            method="GET",
        )
        return url
    except AttributeError:
        pass

    # Fallback: use IAM signBlob (for Cloud Run / Compute Engine credentials)
    credentials, _project = google.auth.default()
    if not credentials.valid:
        credentials.refresh(auth_requests.Request())

    sa_email = getattr(credentials, "service_account_email", None)
    if not sa_email:
        # Last resort: use public URL
        logger.warning("Cannot sign URL, falling back to public URL for %s", blob_path)
        return public_url(bucket_name, blob_path)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=expiration_hours),
        method="GET",
        service_account_email=sa_email,
        access_token=credentials.token,
    )
    return url


def download_bytes(bucket_name: str, blob_path: str) -> bytes:
    """Download a blob from GCS as bytes."""
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()


def build_media_path(
    tenant_id: str,
    media_type: str,
    extension: str,
) -> str:
    """Build a unique GCS object path for media storage.

    Pattern: tenants/{tenant_id}/media/{type}/{uuid}.{ext}
    """
    file_id = uuid.uuid4().hex
    ext = extension.lstrip(".")
    return str(PurePosixPath("tenants", tenant_id, "media", media_type, f"{file_id}.{ext}"))


def public_url(bucket_name: str, blob_path: str) -> str:
    """Return the public HTTPS URL for a GCS object (requires public access)."""
    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
