import io
import os
import urllib.parse

import boto3
import requests

from services.r2_service import get_r2_settings


def _is_public_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"}


def _parse_key_from_url(url: str) -> str | None:
    """
    Attempts to extract the object key from an R2 public URL.
    Returns None if parsing fails.
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return None
    # If the URL already includes the bucket name, strip it
    bucket = os.getenv("R2_BUCKET")
    if bucket and path.startswith(f"{bucket}/"):
        return path[len(bucket) + 1 :]
    return path


def download_file_as_bytes(url: str) -> bytes:
    """
    Download a file either via public HTTP(S) or directly from R2 using boto3.
    Prefers HTTPS to avoid dealing with credentials when possible.
    """
    if not url:
        raise ValueError("Missing URL for download")

    # Fast path: public URL
    if _is_public_url(url):
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.content

    # Fallback: fetch via R2 if the key can be derived
    key = _parse_key_from_url(url)
    if not key:
        raise ValueError("Unable to derive key for resume download")

    endpoint_url, access_key, secret_key, bucket = get_r2_settings()
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    obj = client.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()
