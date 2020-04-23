import requests

from uuid import uuid4

from pymongo.errors import PyMongoError

from celery_worker.celery import app
from celery.utils.log import get_task_logger

from payments.logging import PaymentResultsLoggerAdapter
from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS, PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
    PAYMENTS_SEARCH_FAILED,
    PAYMENTS_GET_COMPLAINT_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_CODE_ERROR,
    PAYMENTS_SEARCH_SUCCESS,
    PAYMENTS_SEARCH_VALID_CODE,
    PAYMENTS_VALID_PAYMENT,
    PAYMENTS_GET_COMPLAINT_SUCCESS,
    PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
    PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
)
from payments.results_db import (
    set_payment_params,
    set_payment_resolution,
    get_payment_item_by_params,
)
from payments.utils import (
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    get_payment_params,
    check_complaint_code,
    check_complaint_value,
    request_complaint_search,
    request_tender_data,
    request_complaint_data,
    request_complaint_patch,
    STATUS_COMPLAINT_MISTAKEN,
    STATUS_COMPLAINT_PENDING,
    ALLOWED_COMPLAINT_RESOLUTION_STATUSES,
    get_resolution,
)
from tasks_utils.requests import get_exponential_request_retry_countdown

logger = get_task_logger(__name__)

try:
    from app.logging import adaptLogger, AppLoggerAdapter
    logger = adaptLogger(logger, AppLoggerAdapter)
    logger = adaptLogger(logger, PaymentResultsLoggerAdapter)
except ImportError:  # pragma: no cover
    pass

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)

COMPLAINT_NOT_FOUND_MAX_RETRIES = 20


@app.task(bind=True, max_retries=1000)
def process_payment_data(self, payment_data, *args, **kwargs):
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
        logger.warning("Invalid pattern for \"{}\"".format(
            description
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_PATTERN
        })
        return

    process_payment_complaint_search.apply_async(kwargs=dict(
        payment_data=payment_data,
        payment_params=payment_params,
    ))


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_search(self, payment_data, payment_params, cookies=None, *args, **kwargs):
    complaint_pretty_id = payment_params.get("complaint")
    client_request_id = uuid4().hex
    try:
        response = request_complaint_search(
            complaint_pretty_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception("Request failed: {}, next retry in {} seconds".format(
            str(exc), countdown
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while searching complaint {}".format(
            response.status_code, complaint_pretty_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                payment_data=payment_data,
                payment_params=payment_params,
                cookies=cookies,
            ))
        countdown = get_exponential_request_retry_countdown(self, response)
        raise self.retry(countdown=countdown)

    search_complaints_data = response.json()["data"]

    if len(search_complaints_data) == 0:
        logger.warning("Invalid payment complaint {}".format(
            complaint_pretty_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_FAILED
        })
        if self.request.retries >= COMPLAINT_NOT_FOUND_MAX_RETRIES:
            logger.warning("Invalid payment complaint {}".format(
                complaint_pretty_id
            ), payment_data=payment_data, task=self, extra={
                "MESSAGE_ID": PAYMENTS_SEARCH_INVALID_COMPLAINT
            })
            return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    search_complaint_data = search_complaints_data[0]

    complaint_params = search_complaint_data.get("params")

    try:
        set_payment_params(payment_data, complaint_params)
    except PyMongoError as exc:
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    logger.info("Successfully found complaint {}".format(
        complaint_pretty_id
    ), payment_data=payment_data, task=self, extra={
        "MESSAGE_ID": PAYMENTS_SEARCH_SUCCESS
    })

    if not check_complaint_code(search_complaint_data, payment_params):
        logger.info("Invalid payment code {} while searching complaint {}".format(
            payment_params.get("code"), complaint_pretty_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_INVALID_CODE
        })
        return

    logger.info("Successfully matched payment code {} for complaint {}".format(
        payment_params.get("code"), complaint_pretty_id
    ), payment_data=payment_data, task=self, extra={
        "MESSAGE_ID": PAYMENTS_SEARCH_VALID_CODE
    })

    process_payment_complaint_data.apply_async(kwargs=dict(
        complaint_params=complaint_params,
        payment_data=payment_data,
        cookies=cookies
    ))


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_data(self, complaint_params, payment_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_complaint_data(
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception("Request failed: {}, next retry in {} seconds".format(
            str(exc), countdown
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while getting complaint {}".format(
            response.status_code, complaint_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                complaint_params=complaint_params,
                payment_data=payment_data,
                cookies=cookies,
            ))
        countdown = get_exponential_request_retry_countdown(self, response)
        raise self.retry(countdown=countdown)
    else:
        logger.info("Successfully retrieved complaint {}".format(
            complaint_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_SUCCESS
        })

    complaint_data = response.json()["data"]

    if not check_complaint_status(complaint_data):
        logger.warning("Invalid complaint status: {}".format(
            complaint_data["status"]
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_STATUS
        })
        return

    if not check_complaint_value(complaint_data):
        logger.info("Invalid complaint value amount or currency for complaint {}".format(
            complaint_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_COMPLAINT_VALUE
        })
        return

    value = complaint_data.get("value", {})

    if not check_complaint_value_amount(complaint_data, payment_data):
        logger.warning("Invalid payment amount for complaint {}: {} not equal {}".format(
            complaint_id, payment_data.get("amount"), value.get("amount")
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_AMOUNT
        })
        process_payment_complaint_patch.apply_async(kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
            patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
            cookies=cookies
        ))
        return

    if not check_complaint_value_currency(complaint_data, payment_data):
        logger.warning("Invalid payment amount for complaint {}: {} not equal {}".format(
            complaint_id, payment_data.get("currency"), value.get("currency")
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_CURRENCY
        })
        process_payment_complaint_patch.apply_async(kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
            patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
            cookies=cookies
        ))
        return

    logger.info("Successfully matched payment for complaint {}".format(
        complaint_id
    ), payment_data=payment_data, task=self, extra={"MESSAGE_ID": PAYMENTS_VALID_PAYMENT})

    process_payment_complaint_patch.apply_async(kwargs=dict(
        payment_data=payment_data,
        complaint_params=complaint_params,
        patch_data={"status": STATUS_COMPLAINT_PENDING},
        cookies=cookies
    ))


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_patch(self, payment_data, complaint_params, patch_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_complaint_patch(
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
            data=patch_data,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception("Request failed: {}, next retry in {} seconds".format(
            str(exc), countdown
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while patching complaint {} of tender {}: {}".format(
            response.status_code, complaint_id, tender_id, patch_data
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data=patch_data,
                cookies=cookies,
            ))
        elif response.status_code == 403:
            process_payment_complaint_recheck.apply_async(kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data=patch_data,
                cookies=cookies
            ))
            return
        else:
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)
    else:
        if patch_data.get("status") == "pending":
            message_id = PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
        else:
            message_id = PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
        logger.info("Successfully updated complaint {} of tender {}: {}".format(
            complaint_id, tender_id, patch_data
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": message_id
        })

@app.task(bind=True, max_retries=1000)
def process_payment_complaint_recheck(self, payment_data, complaint_params, patch_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_complaint_data(
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception("Request failed: {}, next retry in {} seconds".format(
            str(exc), countdown
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    complaint_id = complaint_params.get("complaint_id")
    tender_id = complaint_params.get("tender_id")

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while getting complaint {} of tender {}".format(
            response.status_code, complaint_id, tender_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data=patch_data,
                cookies=cookies,
            ))
        else:
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)
    else:
        complaint_get_data = response.json()["data"]
        if complaint_get_data.get("status") == patch_data.get("status"):
            if patch_data.get("status") == "pending":
                message_id = PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
            else:
                message_id = PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
            logger.info("Successfully updated complaint {} of tender {}: {}".format(
                complaint_id, tender_id, patch_data
            ), payment_data=payment_data, task=self, extra={
                "MESSAGE_ID": message_id
            })
        else:
            process_payment_complaint_data.apply_async(kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                cookies=cookies
            ))


@app.task(bind=True, max_retries=1000)
def process_tender(self, tender_id, *args, **kwargs):
    client_request_id = uuid4().hex
    try:
        response = request_tender_data(
            tender_id,
            client_request_id=client_request_id,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(str(exc), extra={
            "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_EXCEPTION",
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    else:
        if response.status_code != 200:
            logger.warning("Unexpected status code {} while getting tender {}: {}".format(
                response.status_code, tender_id, response.text
            ), extra={
                "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_UNSUCCESSFUL_CODE",
                "STATUS_CODE": response.status_code
            })
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)

        tender = response.json()["data"]

        for complaint_data in tender.get("complaints", []):
            if complaint_data["status"] in ALLOWED_COMPLAINT_RESOLUTION_STATUSES:
                complaint_params = {
                    "item_id": None,
                    "item_type": None,
                    "complaint_id": complaint_data["id"],
                    "tender_id": tender_id
                }
                process_complaint_params.apply_async(
                    kwargs=dict(
                        complaint_params=complaint_params,
                        complaint_data=complaint_data
                    )
                )

        for item_type in ["qualifications", "awards", "cancellations"]:
            for item_data in tender.get(item_type, []):
                for complaint_data in item_data.get("complaints", []):
                    if complaint_data["status"] in ALLOWED_COMPLAINT_RESOLUTION_STATUSES:
                        complaint_params = {
                            "item_id": item_data["id"],
                            "item_type": item_type,
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id
                        }
                        process_complaint_params.apply_async(
                            kwargs=dict(
                                complaint_params=complaint_params,
                                complaint_data=complaint_data
                            )
                        )


@app.task(bind=True, max_retries=1000)
def process_complaint_params(self, complaint_params, complaint_data):
    try:
        payment = get_payment_item_by_params(complaint_params, [
            PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
            PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
        ])
    except PyMongoError as exc:
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    if payment:
        if not payment.get("resolution"):
            process_complaint_resolution.apply_async(
                kwargs=dict(
                    payment_data=payment.get("payment"),
                    complaint_data=complaint_data
                )
            )
    else:
        logger.warning("Payment not found for complaint {} with params".format(
            complaint_data["id"], complaint_params
        ), extra={
            "MESSAGE_ID": "PAYMENTS_CRAWLER_PAYMENT_NOT_FOUND"
        })


@app.task(bind=True, max_retries=1000)
def process_complaint_resolution(self, payment_data, complaint_data, *args, **kwargs):
    resolution = get_resolution(complaint_data)
    if resolution:
        try:
            set_payment_resolution(payment_data, resolution)
        except PyMongoError as exc:
            countdown = get_exponential_request_retry_countdown(self)
            raise self.retry(countdown=countdown, exc=exc)
        logger.info("Successfully saved complaint {} resolution".format(
            complaint_data["id"]
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS
        })
