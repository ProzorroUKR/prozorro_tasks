from tasks_utils.settings import (
    RETRY_REQUESTS_EXCEPTIONS, DEFAULT_HEADERS,
)
from environment_settings import (
    PUBLIC_API_HOST, API_VERSION,
    DS_HOST, DS_USER, DS_PASSWORD,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD, CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER,
    EXPONENTIAL_RETRY_BASE, EXPONENTIAL_RETRY_MAX,
)
from celery.utils.log import get_task_logger
from urllib.parse import unquote
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
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
    countdown = DEFAULT_RETRY_AFTER
    if request:
        try:
            countdown = float(request.headers.get('Retry-After'))
        except (TypeError, ValueError, AttributeError):
            pass
    return countdown


def get_exponential_request_retry_countdown(task, request=None):
    countdown = get_request_retry_countdown(request)
    retries = task.request.retries
    if retries:
        countdown += EXPONENTIAL_RETRY_BASE ** retries
    return min(countdown, EXPONENTIAL_RETRY_MAX)


def get_task_retry_logger_method(
    task_obj, logger_obj,
    default_method='warning',
    fallback_method='error'
):
    max_retries = getattr(task_obj, "max_retries", None)
    if max_retries and task_obj.request.retries < max_retries:
        return getattr(logger_obj, default_method)
    return getattr(logger_obj, fallback_method)


def get_public_api_data(task, uid, document_type="tender"):
    try:
        response = requests.get(
            f"{PUBLIC_API_HOST}/api/{API_VERSION}/{document_type}s/{uid}",
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "GET_DOC_EXCEPTION"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(task, logger)
            logger_method(
                f"Unexpected status code {response.status_code} while getting {document_type} {uid}: {response.text}",
                extra={
                    "MESSAGE_ID": "GET_DOC_UNSUCCESSFUL_CODE",
                    "STATUS_CODE": response.status_code,
                })
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            try:
                resp_json = response.json()
            except json.decoder.JSONDecodeError:
                logger.error(
                    "JSONDecodeError on edr request with status {}: ".format(response.status_code),
                    extra={"MESSAGE_ID": "RESP_JSON_DECODE_EXCEPTION"}
                )
                raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
            else:
                return resp_json["data"]


def download_file(task, url):
    try:
        response = requests.get(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "GET_FILE_EXCEPTION"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(task, logger)
            logger_method(
                f"Unexpected code {response.status_code} while getting file {url}: {response.text}",
                extra={
                    "MESSAGE_ID": "GET_FILE_UNSUCCESSFUL_CODE",
                    "STATUS_CODE": response.status_code,
                })
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            return get_filename_from_response(response), response.content


def ds_upload(task, file_name, file_content):
    try:
        response = requests.post(
            '{host}/upload'.format(host=DS_HOST),
            auth=(DS_USER, DS_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            files={'file': (file_name, file_content)},
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "POST_DOC_API_ERROR"})
        raise task.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(task, logger)
            logger_method(
                f"Incorrect upload status for doc {file_name}",
                extra={
                    "MESSAGE_ID": "POST_DOC_API_ERROR",
                    "STATUS_CODE": response.status_code,
                })
            raise task.retry(countdown=get_request_retry_countdown(response))

        response_json = response.json()
        return response_json["data"]


def sign_data(task, data):
    try:
        response = requests.post(
            "{}/sign/file".format(API_SIGN_HOST),
            files={'file': ('name', data)},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "SIGN_DATA_REQUEST_ERROR"})
        raise task.retry(exc=e, countdown=get_exponential_request_retry_countdown(task))
    else:
        if response.status_code != 200:
            logger.error(
                "Signing failure: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "SIGN_DATA_ERROR"}
            )
            raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
        else:
            return response.content


def get_json_or_retry(task, response):
    try:
        resp_json = response.json()
    except json.decoder.JSONDecodeError:
        logger_method = get_task_retry_logger_method(task, logger)
        logger_method(
            "JSONDecodeError of response",
            extra={
                "MESSAGE_ID": "RESP_JSON_DECODE_EXCEPTION",
                "STATUS_CODE": response.status_code,
            }
        )
        raise task.retry(countdown=get_exponential_request_retry_countdown(task, response))
    else:
        return resp_json


def mount_retries_for_request(session, total_retries=10, backoff_factor=10,
                              status_forcelist=(408, 409, 412, 429, 500, 502, 503, 504)):
    retry_strategy = Retry(
        total=total_retries, backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_redirect=False, raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
