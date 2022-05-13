from uuid import uuid4

import requests
from celery.utils.log import get_task_logger

from celery_worker.celery import app
from environment_settings import API_HOST, API_VERSION, CHRONOGRAPH_API_TOKEN, CONNECT_TIMEOUT, READ_TIMEOUT
from tasks_utils.requests import (
    get_task_retry_logger_method,
    get_exponential_request_retry_countdown,
)
from tasks_utils.settings import RETRY_REQUESTS_EXCEPTIONS, DEFAULT_HEADERS

logger = get_task_logger(__name__)


CHRONOGRAPH_CHECK_MAX_RETRIES = None
CHRONOGRAPH_CHECK_MAX_RETRIES_404 = 10


@app.task(bind=True, max_retries=CHRONOGRAPH_CHECK_MAX_RETRIES)
def recheck(self, obj_name, obj_id, cookies=None):
    url = "{host}/api/{version}/{object_name}s/{object_id}".format(
        host=API_HOST,
        version=API_VERSION,
        object_name=obj_name,
        object_id=obj_id,
    )
    obj_name_upper = obj_name.upper()

    try:
        response = requests.get(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            cookies=cookies or {},
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "CHRONOGRAPH_{}_GET_EXCEPTION".format(obj_name_upper)})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while getting {} {}".format(
                response.status_code, obj_name, obj_id
            ), extra={
                "MESSAGE_ID": "CHRONOGRAPH_{}_GET_CODE_ERROR".format(obj_name_upper),
                "STATUS_CODE": response.status_code,
            })
            if response.status_code == 412:  # Precondition failed
                retry_kwargs = dict(**self.request.kwargs)
                retry_kwargs["cookies"] = response.cookies.get_dict()
                raise self.retry(countdown=0, kwargs=retry_kwargs)
            elif response.status_code == 404:
                if self.request.retries > CHRONOGRAPH_CHECK_MAX_RETRIES_404:
                    return
            raise self.retry(countdown=get_exponential_request_retry_countdown(response))

    cookies = response.cookies.get_dict()

    if "next_check" not in response.json()["data"]:
        logger.warning("Skip {} {} without next_check".format(
            obj_name, obj_id
        ), extra={
            "MESSAGE_ID": "CHRONOGRAPH_{}_SKIP".format(obj_name_upper),
        })
        return

    try:
        response = requests.patch(
            url,
            json={"data": {}},
            headers={
                "Authorization": "Bearer {}".format(CHRONOGRAPH_API_TOKEN),
                "X-Client-Request-ID": uuid4().hex,
                **DEFAULT_HEADERS,
            },
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            cookies=cookies
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "CHRONOGRAPH_{}_CHECK_EXCEPTION".format(obj_name_upper)})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while checking {} {}".format(
                response.status_code, obj_name, obj_id
            ), extra={
                "MESSAGE_ID": "CHRONOGRAPH_{}_CHECK_CODE_ERROR".format(obj_name_upper),
                "STATUS_CODE": response.status_code,
            })
            if response.status_code == 412:  # Precondition failed
                retry_kwargs = dict(**self.request.kwargs)
                retry_kwargs["cookies"] = response.cookies.get_dict()
                raise self.retry(countdown=0, kwargs=retry_kwargs)
            raise self.retry(countdown=get_exponential_request_retry_countdown(self, response))
