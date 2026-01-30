import os
import boto3


def get_r2_settings():
    endpoint_url = os.getenv("R2_ENDPOINT_URL")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET")

    if not endpoint_url or not access_key or not secret_key or not bucket:
        raise ValueError("Missing Cloudflare R2 environment variables")

    return endpoint_url, access_key, secret_key, bucket


def build_public_url(endpoint_url: str, bucket: str, key: str) -> str:
    public_base_url = "https://pub-4e784ee4f6b24479b0e9573fac4a96e8.r2.dev/"
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{key}"
    return f"{endpoint_url.rstrip('/')}/{bucket}/{key}"


def upload_pdf_bytes(file_bytes: bytes, key: str) -> str:
    endpoint_url, access_key, secret_key, bucket = get_r2_settings()
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType="application/pdf",
    )
    return build_public_url(endpoint_url, bucket, key)


def upload_bytes(file_bytes: bytes, key: str, content_type: str) -> str:
    endpoint_url, access_key, secret_key, bucket = get_r2_settings()
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return build_public_url(endpoint_url, bucket, key)
