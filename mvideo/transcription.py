from __future__ import annotations

import json
import os
import sys
import uuid
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from urllib import request

from loguru import logger

if TYPE_CHECKING:
    import alibabacloud_oss_v2 as oss


def get_oss_client() -> tuple[oss.Client, str]:
    """Get an OSS client and bucket name from environment variables."""
    import alibabacloud_oss_v2 as oss

    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    endpoint = os.getenv("OSS_ENDPOINT")
    bucket_name = os.getenv("OSS_BUCKET_NAME")
    if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
        logger.error(
            "OSS environment variables not set. Required: "
            "OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET_NAME"
        )
        sys.exit(1)

    credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id, access_key_secret
    )
    config = oss.config.load_default()
    config.credentials_provider = credentials_provider
    config.endpoint = endpoint
    config.region = os.getenv("OSS_REGION", "cn-hangzhou")
    return oss.Client(config), str(bucket_name)


def upload_file_to_oss(
    file_path: str,
    object_key: str | None = None,
) -> tuple[str, str]:
    """Upload a file to OSS and return its object key and public URL."""
    import alibabacloud_oss_v2 as oss

    client, bucket_name = get_oss_client()
    if object_key is None:
        object_key = f"mvideo/temp/{uuid.uuid4().hex}{Path(file_path).suffix}"

    logger.info(f"Uploading {file_path} to OSS: {object_key}")
    with open(file_path, "rb") as file:
        result = client.put_object(
            oss.PutObjectRequest(bucket=bucket_name, key=object_key, body=file)
        )
    if result.status_code != 200:
        logger.error(f"Failed to upload file to OSS: {result}")
        sys.exit(1)

    endpoint = os.getenv("OSS_ENDPOINT", "")
    endpoint_host = endpoint.replace("https://", "").replace("http://", "")
    public_url = f"https://{bucket_name}.{endpoint_host}/{object_key}"
    logger.success(f"File uploaded: {public_url}")
    return object_key, public_url


def delete_oss_file(object_key: str) -> None:
    """Delete a file from OSS."""
    import alibabacloud_oss_v2 as oss

    client, bucket_name = get_oss_client()
    try:
        client.delete_object(
            oss.DeleteObjectRequest(bucket=bucket_name, key=object_key)
        )
        logger.info(f"Deleted OSS file: {object_key}")
    except Exception as error:  # noqa: BLE001 - cleanup must not mask transcription
        logger.warning(f"Failed to delete OSS file {object_key}: {error}")


def transcribe_audio_func(
    audio_file: str,
    language_hints: list[str] | None = None,
) -> list[dict]:
    """Transcribe an audio file using the DashScope ASR SDK."""
    import dashscope
    from dashscope.audio.asr import Transcription

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("DASHSCOPE_API_KEY environment variable is not set")
        sys.exit(1)

    dashscope.api_key = api_key
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    if language_hints is None:
        language_hints = ["zh", "en"]

    logger.info("Uploading audio file to OSS...")
    object_key, oss_url = upload_file_to_oss(audio_file)
    logger.info(f"Audio uploaded: {oss_url}")

    try:
        logger.info("Starting transcription...")
        task_response = Transcription.async_call(
            model="fun-asr",
            file_urls=[oss_url],
            language_hints=language_hints,
        )
        if task_response.status_code != HTTPStatus.OK:
            logger.error(
                f"Failed to start transcription: {task_response.output.message}"
            )
            sys.exit(1)

        logger.info(f"Task created: {task_response.output.task_id}")
        logger.info("Waiting for transcription to complete...")
        transcription_response = Transcription.wait(task=task_response.output.task_id)
        if transcription_response.status_code != HTTPStatus.OK:
            logger.error(
                f"Transcription failed: {transcription_response.output.message}"
            )
            sys.exit(1)

        logger.success("Transcription completed successfully")
        results = []
        for transcription in transcription_response.output.get("results", []):
            if transcription.get("subtask_status") == "SUCCEEDED":
                url = transcription.get("transcription_url")
                if url:
                    result = json.loads(request.urlopen(url).read().decode("utf8"))
                    results.append(result)
            else:
                logger.warning(f"Subtask failed: {transcription}")
        return results
    finally:
        delete_oss_file(object_key)
