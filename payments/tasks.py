import requests

from uuid import uuid4

from celery_worker.celery import app
from celery.utils.log import get_task_logger

from payments.utils import (
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    get_payment_params,
    check_complaint_code,
    check_complaint_value,
)
from tasks_utils.requests import get_exponential_request_retry_countdown
from tasks_utils.settings import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
)
from environment_settings import (
    PUBLIC_API_HOST,
    API_VERSION,
    API_TOKEN,
    API_HOST,
)

logger = get_task_logger(__name__)

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True, max_retries=20)
def process_payment_data(self, payment_data):
    """
    Process and validate payment data

    :param self:
    :param payment_data: dict

    Example:
    >>> {
    ...     "amount": "123",
    ...     "currency": "UAH",
    ...     "description": "UA-2020-03-17-000090-a.a2-12AD3F12"
    ... }

    :return:
    """
    description = payment_data.get("description", "")
    payment_params = get_payment_params(description)

    if not payment_params:
        logger.warning("No valid pattern found for \"{}\"".format(
            description
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_PATTERN"})
        return

    if self.request.is_eager:
        return payment_params

    process_payment_complaint_search.apply_async(kwargs=dict(
        payment_data=payment_data,
        payment_params=payment_params,
    ))


@app.task(bind=True, max_retries=20)
def process_payment_complaint_search(self, payment_data, payment_params):
    complaint_pretty_id = payment_params.get("complaint")

    url = "{host}/api/{version}/complaints/search?complaint_id={complaint_pretty_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        complaint_pretty_id=complaint_pretty_id
    )

    client_request_id = uuid4().hex
    try:
        response = requests.get(
            url,
            headers={
                "X-Client-Request-ID": client_request_id,
                "Authorization": "Bearer {}".format(API_TOKEN),
            },
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            logger.exception(exc, extra={
                "MESSAGE_ID": "PAYMENTS_SEARCH_EXCEPTION",
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            })
            if not self.request.is_eager:
                return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while searching complaint {}".format(
            response.status_code, complaint_pretty_id
        ), extra={
            "MESSAGE_ID": "PAYMENTS_SEARCH_CODE_ERROR",
            "STATUS_CODE": response.status_code
        })
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    search_complaints_data = response.json()["data"]

    if len(search_complaints_data) == 0:
        logger.warning("Invalid payment complaint {}".format(
            complaint_pretty_id
        ), extra={"MESSAGE_ID": "PAYMENTS_SEARCH_INVALID_COMPLAINT"})
        return

    for search_complaint_data in search_complaints_data:
        logger.info("Successfully retrieved complaint {} params".format(
            complaint_pretty_id
        ), extra={"MESSAGE_ID": "PAYMENTS_SEARCH_SUCCESS"})

        if self.request.is_eager:
            return search_complaint_data

        if not check_complaint_code(search_complaint_data, payment_params):
            logger.info("Invalid payment code {} while searching complaint {}".format(
                payment_params.get("code"), complaint_pretty_id
            ), extra={"MESSAGE_ID": "PAYMENTS_SEARCH_INVALID_CODE"})
            return

        logger.info("Valid payment code {} while searching complaint {}".format(
            payment_params.get("code"), complaint_pretty_id
        ), extra={"MESSAGE_ID": "PAYMENTS_SEARCH_VALID_CODE"})

        complaint_params = search_complaint_data.get("params")

        process_payment_complaint_data.apply_async(kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
        ))


@app.task(bind=True, max_retries=20)
def process_payment_complaint_data(self, payment_data, complaint_params):
    tender_id = complaint_params.get("tender_id")

    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=tender_id
    )

    client_request_id = uuid4().hex
    try:
        response = requests.get(
            url,
            headers={"X-Client-Request-ID": client_request_id},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            logger.exception(exc, extra={
                "MESSAGE_ID": "PAYMENTS_GET_TENDER_EXCEPTION",
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            })
            if not self.request.is_eager:
                return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while getting tender {}".format(
            response.status_code, tender_id
        ), extra={
            "MESSAGE_ID": "PAYMENTS_GET_TENDER_CODE_ERROR",
            "STATUS_CODE": response.status_code
        })
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)
    else:
        logger.info("Successfully retrieved tender {}".format(
            tender_id
        ), extra={"MESSAGE_ID": "PAYMENTS_GET_TENDER_SUCCESS"})

    tender_data = response.json()["data"]

    complaint_id = complaint_params.get("complaint_id")

    if complaint_params.get("item_type"):
        item_type = complaint_params.get("item_type")
        item_id = complaint_params.get("item_id")
        item_data = get_item_data(tender_data, item_type, item_id)
        if not item_data:
            logger.warning("No {} with id {} found in tender {}".format(
                item_type, item_id,  tender_id
            ), extra={"MESSAGE_ID": "PAYMENTS_ITEM_NOT_FOUND"})
            countdown = get_exponential_request_retry_countdown(self)
            raise self.retry(countdown=countdown)
        complaint_data =  get_item_data(item_data, "complaints", complaint_id)
    else:
        complaint_data = get_item_data(tender_data, "complaints", complaint_id)

    if not complaint_data:
        logger.warning("No complaints with id found {} in tender {}".format(
            complaint_id, tender_id
        ), extra={"MESSAGE_ID": "PAYMENTS_COMPLAINT_NOT_FOUND"})
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    if self.request.is_eager:
        logger.info("Valid complaint value found for complaint {}.".format(
            complaint_id
        ), extra={"MESSAGE_ID": "PAYMENTS_VALID_COMPLAINT"})
        return complaint_data

    if not check_complaint_status(complaint_data):
        logger.warning("Complaint status is not valid: {}.".format(
            complaint_data["status"]
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_STATUS"})
        return

    if not check_complaint_value(complaint_data):
        logger.info("Complaint value amount or currency not found for complaint {}.".format(
            complaint_id
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_COMPLAINT_VALUE"})
        return

    value = complaint_data.get("value", {})

    if not check_complaint_value_amount(complaint_data, payment_data):
        logger.warning("Payment amount doesn't match complaint amount ({} and {}) in complaint {}.".format(
            payment_data.get("amount"), value.get("amount"), complaint_id
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_AMOUNT"})
        process_payment_complaint_patch.apply_async(kwargs=dict(
            complaint_params=complaint_params,
            complaint_patch_data={
                "status": "mistaken"
            }
        ))
        return

    if not check_complaint_value_currency(complaint_data, payment_data):
        logger.warning("Payment currency doesn't match complaint currency ({} and {}) in complaint {}.".format(
            payment_data.get("currency"), value.get("currency"), complaint_id
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_CURRENCY"})
        process_payment_complaint_patch.apply_async(kwargs=dict(
            complaint_params=complaint_params,
            complaint_patch_data={
                "status": "mistaken"
            }
        ))
        return

    logger.info("Valid payment found for complaint {}.".format(
        complaint_id
    ), extra={"MESSAGE_ID": "PAYMENTS_VALID_PAYMENT"})

    process_payment_complaint_patch.apply_async(kwargs=dict(
        complaint_params=complaint_params,
        complaint_patch_data={
            "status": "pending"
        }
    ))


@app.task(bind=True, max_retries=20)
def process_payment_complaint_patch(self, complaint_params, complaint_patch_data):
    if complaint_params.get("item_type"):
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"

    url = url_pattern.format(
        host=API_HOST,
        version=API_VERSION,
        **complaint_params
    )
    
    client_request_id = uuid4().hex
    try:
        head_response = requests.head(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                "Authorization": "Bearer {}".format(API_TOKEN),
                "X-Client-Request-ID": client_request_id,
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            logger.exception(exc, extra={
                "MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION",
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            })
            if not self.request.is_eager:
                return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    cookies = head_response.cookies
    
    client_request_id = uuid4().hex
    try:
        response = requests.patch(
            url,
            json={"data": complaint_patch_data},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                "Authorization": "Bearer {}".format(API_TOKEN),
                "X-Client-Request-ID": client_request_id,
            },
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        if self.request.retries >= self.max_retries:
            logger.exception(exc, extra={
                "MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_EXCEPTION",
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            })
            if not self.request.is_eager:
                return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    complaint_id = complaint_params.get("complaint_id")
    tender_id = complaint_params.get("tender_id")

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while patching complaint {} of tender {}: {}".format(
            response.status_code, complaint_id, tender_id, complaint_patch_data
        ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_CODE_ERROR",
                  "STATUS_CODE": response.status_code})
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)
    else:
        logger.info("Successfully updated complaint {} of tender {}: {}".format(
            complaint_id, tender_id, complaint_patch_data
        ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_SUCCESS"})
