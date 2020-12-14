from uuid import uuid4

import requests
from celery.utils.log import get_task_logger

from celery_worker.celery import app
from environment_settings import API_HOST, API_VERSION, CHRONOGRAPH_API_TOKEN
from tasks_utils.requests import (
    get_task_retry_logger_method,
    get_exponential_request_retry_countdown,
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT, RETRY_REQUESTS_EXCEPTIONS

logger = get_task_logger(__name__)


CHRONOGRAPH_CHECK_MAX_RETRIES = None


@app.task(bind=True, max_retries=CHRONOGRAPH_CHECK_MAX_RETRIES)
def recheck_framework(self, framework_id, cookies=None):
    url = "{host}/api/{version}/frameworks/{framework_id}".format(
        host=API_HOST,
        version=API_VERSION,
        framework_id=framework_id,
    )

    try:
        response = requests.get(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            cookies=cookies or {}
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "CHRONOGRAPH_FRAMEWORK_GET_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while getting framework {}".format(
                response.status_code, framework_id
            ), extra={
                "MESSAGE_ID": "CHRONOGRAPH_FRAMEWORK_GET_CODE_ERROR",
                "STATUS_CODE": response.status_code,
            })
            raise self.retry(countdown=get_exponential_request_retry_countdown(response))

    cookies = response.cookies.get_dict()

    if "next_check" not in response.json()["data"]:
        logger.warning("Skip framework {} without next_check".format(
            framework_id
        ), extra={
            "MESSAGE_ID": "CHRONOGRAPH_FRAMEWORK_SKIP",
        })
        return

    try:
        response = requests.patch(
            url,
            json={"data": {}},
            headers={
                "Authorization": "Bearer {}".format(CHRONOGRAPH_API_TOKEN),
                "X-Client-Request-ID": uuid4().hex
            },
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            cookies=cookies
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "CHRONOGRAPH_FRAMEWORK_CHECK_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while checking framework {}".format(
                response.status_code, framework_id
            ), extra={
                "MESSAGE_ID": "CHRONOGRAPH_FRAMEWORK_CHECK_CODE_ERROR",
                "STATUS_CODE": response.status_code,
            })
            if response.status_code == 412:  # Precondition failed
                retry_kwargs = dict(**self.request.kwargs)
                retry_kwargs["cookies"] = response.cookies.get_dict()
                raise self.retry(countdown=0, kwargs=retry_kwargs)
            raise self.retry(countdown=get_exponential_request_retry_countdown(response))
