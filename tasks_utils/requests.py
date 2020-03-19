from tasks_utils.settings import (
    CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER, RETRY_REQUESTS_EXCEPTIONS,
    EXPONENTIAL_RETRY_BASE, EXPONENTIAL_RETRY_MAX,
)
from environment_settings import PUBLIC_API_HOST, API_VERSION
from celery.utils.log import get_task_logger
from urllib.parse import unquote
import requests
import json
import re

logger = get_task_logger(__name__)


def get_filename_from_response(response):
    disposition = response.headers.get('content-disposition')
    if disposition:
        result = re.findall(
            r"filename=(?P<filename>[^;]+)(; filename\*=(?P<encoding>.+)''(?P<encoded_filename>.*))?",
            disposition
        )
        if result:
            filename, _, encoding, encoded_name = result[0]
            if encoding and encoded_name:
                return unquote(encoded_name, encoding=encoding)
            else:
                return filename


def get_request_retry_countdown(request=None):
    try:
        countdown = float(request.headers.get('Retry-After'))
    except (TypeError, ValueError, AttributeError):
        countdown = DEFAULT_RETRY_AFTER
    return countdown


def get_exponential_request_retry_countdown(task, request=None):
    countdown = get_request_retry_countdown(request)
    retries = task.request.retries
    if retries:
        countdown += EXPONENTIAL_RETRY_BASE ** retries
    return min(countdown, EXPONENTIAL_RETRY_MAX)


def get_public_api_data(task, uid, document_type="tender"):
    try:
        response = requests.get(
            f"{PUBLIC_API_HOST}/api/{API_VERSION}/{document_type}s/{uid}",
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "GET_DOC_EXCEPTION"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error(
                f"Unexpected code {response.status_code} while getting {document_type} {uid}: {response.text}",
                extra={"MESSAGE_ID": "GET_DOC_UNSUCCESSFUL_CODE",
                       "STATUS_CODE": response.status_code})
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            try:
                resp_json = response.json()
            except json.decoder.JSONDecodeError:
                logger.error(
                    "JSONDecodeError on edr request with status {}: ".format(response.status_code),
                    extra={"MESSAGE_ID": "RESP_JSON_DECODE_EXCEPTION"}
                )
                task.retry(countdown=get_exponential_request_retry_countdown(task, response))
            else:
                return resp_json["data"]


def download_file(task, url):
    try:
        response = requests.get(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "GET_FILE_EXCEPTION"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error(
                f"Unexpected code {response.status_code} while getting file {url}: {response.text}",
                extra={"MESSAGE_ID": "GET_FILE_UNSUCCESSFUL_CODE",
                       "STATUS_CODE": response.status_code})
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            return get_filename_from_response(response), response.content
