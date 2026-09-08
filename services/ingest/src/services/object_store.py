import json
from collections.abc import Iterable
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

from src.config import get_settings


def client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.object_store_endpoint or None,
        aws_access_key_id=settings.object_store_access_key,
        aws_secret_access_key=settings.object_store_secret_key,
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )


def put_jsonl(bucket: str, key: str, records: Iterable[dict[str, Any]]) -> int | None:
    body = "\n".join(json.dumps(record, default=str) for record in records).encode()
    try:
        client().put_object(Bucket=bucket, Key=key, Body=body)
    except ClientError as error:
        logger.bind(bucket=bucket, key=key, error=str(error)).debug("object store write failed")
        return None
    return len(body)


def get_jsonl(bucket: str, key: str) -> list[dict[str, Any]]:
    body = client().get_object(Bucket=bucket, Key=key)["Body"].read().decode()
    return [json.loads(line) for line in body.splitlines() if line]
