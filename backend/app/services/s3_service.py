import io

import boto3
from flask import current_app


def _get_client():
    return boto3.client("s3", region_name=current_app.config["AWS_REGION"])


def upload_file(file_obj, s3_key):
    """Upload a file-like object to S3 at s3_key."""
    client = _get_client()
    bucket = current_app.config["S3_BUCKET_NAME"]
    client.upload_fileobj(file_obj, bucket, s3_key)


def get_file_bytes(s3_key):
    """Stream an S3 object into a BytesIO buffer, rewound to position 0."""
    client = _get_client()
    bucket = current_app.config["S3_BUCKET_NAME"]
    response = client.get_object(Bucket=bucket, Key=s3_key)
    buf = io.BytesIO(response["Body"].read())
    buf.seek(0)
    return buf
