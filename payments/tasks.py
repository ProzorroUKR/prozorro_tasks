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
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
)
from payments.results_db import set_payment_params, set_payment_resolution, get_payment_item_by_params
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
    DEFAULT_RETRY_AFTER,
)
from environment_settings import (
    PUBLIC_API_HOST,
    API_VERSION,
    API_TOKEN,
    API_HOST,
)

logger = get_task_logger(__name__)

try:
    from app.logging import adaptLogger, AppLoggerAdapter
    logger = adaptLogger(logger, AppLoggerAdapter)
    logger = adaptLogger(logger, PaymentResultsLoggerAdapter)
except ImportError:
    pass

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)

COMPLAINT_NOT_FOUND_MAX_RETRIES = 20


@app.task(bind=True, max_retries=None)
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

    if self.request.is_eager:
        return payment_params

    process_payment_complaint_search.apply_async(kwargs=dict(
        payment_data=payment_data,
        payment_params=payment_params,
    ))


@app.task(bind=True, max_retries=None)
def process_payment_complaint_search(self, payment_data, payment_params, cookies=None, *args, **kwargs):
    complaint_pretty_id = payment_params.get("complaint")

    url = "{host}/api/{version}/complaints/search?complaint_id={complaint_pretty_id}".format(
        host=API_HOST,
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
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(str(exc), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        if self.request.is_eager:
            raise
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    cookies = response.cookies.get_dict()

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while searching complaint {}".format(
            response.status_code, complaint_pretty_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if self.request.is_eager:
            return
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                payment_data=payment_data,
                payment_params=payment_params,
                cookies=cookies,
            ))
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    search_complaints_data = response.json()["data"]

    if len(search_complaints_data) == 0:
        logger.warning("Invalid payment complaint {}".format(
            complaint_pretty_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_SEARCH_INVALID_COMPLAINT
        })
        if self.request.is_eager:
            return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    search_complaint_data = search_complaints_data[0]

    complaint_params = search_complaint_data.get("params")

    if not self.request.is_eager:
        try:
            set_payment_params(payment_data, complaint_params)
        except PyMongoError as exc:
            countdown = get_exponential_request_retry_countdown(self)
            raise self.retry(countdown=countdown, exc=exc)

    logger.info("Successfully found complaint {}".format(
        complaint_pretty_id
    ), payment_data=payment_data, task=self, extra={
        "MESSAGE_ID": "PAYMENTS_SEARCH_SUCCESS"
    })

    if self.request.is_eager:
        return search_complaint_data

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
        "MESSAGE_ID": "PAYMENTS_SEARCH_VALID_CODE"
    })

    process_payment_complaint_data.apply_async(kwargs=dict(
        complaint_params=complaint_params,
        payment_data=payment_data,
        cookies=cookies
    ))


@app.task(bind=True, max_retries=None)
def process_payment_complaint_data(self, complaint_params, payment_data, cookies=None, *args, **kwargs):
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
            cookies=cookies
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(str(exc), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_TENDER_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        if self.request.is_eager:
            raise
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    cookies = response.cookies.get_dict()

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while getting tender {}".format(
            response.status_code, tender_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_GET_TENDER_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if self.request.is_eager:
            return
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                complaint_params=complaint_params,
                payment_data=payment_data,
                cookies=cookies,
            ))
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)
    else:
        logger.info("Successfully retrieved tender {}".format(
            tender_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": "PAYMENTS_GET_TENDER_SUCCESS"
        })

    tender_data = response.json()["data"]

    complaint_id = complaint_params.get("complaint_id")

    if complaint_params.get("item_type"):
        item_type = complaint_params.get("item_type")
        item_id = complaint_params.get("item_id")
        item_data = get_item_data(tender_data, item_type, item_id)
        if not item_data:
            logger.warning("Invalid {} id {} for tender {}".format(
                item_type[:-1], item_id,  tender_id
            ), payment_data=payment_data, task=self, extra={
                "MESSAGE_ID": PAYMENTS_ITEM_NOT_FOUND
            })
            if self.request.is_eager:
                return
            countdown = get_exponential_request_retry_countdown(self)
            raise self.retry(countdown=countdown)
        complaint_data =  get_item_data(item_data, "complaints", complaint_id)
        logger.info("Successfully retrieved {} {}".format(
            item_type[:-1], item_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": "PAYMENTS_VALID_ITEM"
        })
    else:
        complaint_data = get_item_data(tender_data, "complaints", complaint_id)

    if not complaint_data:
        logger.warning("Invalid complaint id {} for tender {}".format(
            complaint_id, tender_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_COMPLAINT_NOT_FOUND
        })
        if self.request.is_eager:
            return
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    if self.request.is_eager:
        logger.info("Successfully found complaint data {}.".format(
            complaint_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": "PAYMENTS_VALID_COMPLAINT"
        })
        return complaint_data

    if not check_complaint_status(complaint_data):
        logger.warning("Invalid complaint status: {}.".format(
            complaint_data["status"]
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_STATUS
        })
        return

    if not check_complaint_value(complaint_data):
        logger.info("Invalid complaint value amount or currency for complaint {}.".format(
            complaint_id
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_COMPLAINT_VALUE
        })
        return

    value = complaint_data.get("value", {})

    if not check_complaint_value_amount(complaint_data, payment_data):
        logger.warning("Invalid payment amount for complaint {}: {} not equal {}.".format(
            complaint_id, payment_data.get("amount"), value.get("amount")
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_AMOUNT
        })
        process_payment_complaint_patch.apply_async(kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
            complaint_patch_data={
                "status": "mistaken"
            },
            cookies=cookies
        ))
        return

    if not check_complaint_value_currency(complaint_data, payment_data):
        logger.warning("Invalid payment amount for complaint {}: {} not equal {}.".format(
            complaint_id, payment_data.get("currency"), value.get("currency")
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_INVALID_CURRENCY
        })
        process_payment_complaint_patch.apply_async(kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
            complaint_patch_data={
                "status": "mistaken"
            },
            cookies=cookies
        ))
        return

    logger.info("Successfully matched payment for complaint {}.".format(
        complaint_id
    ), payment_data=payment_data, task=self, extra={"MESSAGE_ID": "PAYMENTS_VALID_PAYMENT"})

    process_payment_complaint_patch.apply_async(kwargs=dict(
        payment_data=payment_data,
        complaint_params=complaint_params,
        complaint_patch_data={
            "status": "pending"
        },
        cookies=cookies
    ))


@app.task(bind=True, max_retries=None)
def process_payment_complaint_patch(self, payment_data, complaint_params, complaint_patch_data, cookies=None,
                                    *args, **kwargs):
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
        logger.exception(str(exc), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
            "CDB_CLIENT_REQUEST_ID": client_request_id,
        })
        if self.request.is_eager:
            raise
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)

    cookies = response.cookies.get_dict()

    complaint_id = complaint_params.get("complaint_id")
    tender_id = complaint_params.get("tender_id")

    if response.status_code != 200:
        logger.warning("Unexpected status code {} while patching complaint {} of tender {}: {}".format(
            response.status_code, complaint_id, tender_id, complaint_patch_data
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
            "STATUS_CODE": response.status_code
        })
        if self.request.is_eager:
            return
        if response.status_code == 412:
            raise self.retry(countdown=0, kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                complaint_patch_data=complaint_patch_data,
                cookies=cookies,
            ))
        elif response.status_code == 403:
            process_payment_complaint_data.apply_async(kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                cookies=cookies
            ))
            return
        else:
            countdown = get_exponential_request_retry_countdown(self)
            raise self.retry(countdown=countdown)
    else:
        if complaint_patch_data.get("status") == "pending":
            message_id = PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
        else:
            message_id = PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
        logger.info("Successfully updated complaint {} of tender {}: {}".format(
            complaint_id, tender_id, complaint_patch_data
        ), payment_data=payment_data, task=self, extra={
            "MESSAGE_ID": message_id
        })


@app.task(bind=True, max_retries=None)
def process_tender(self, tender_id, *args, **kwargs):
    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=tender_id,
    )

    try:
        response = requests.get(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(str(exc), task=self, extra={
            "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_EXCEPTION"
        })
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    else:
        if response.status_code != 200:
            logger.warning("Unexpected status code {} while getting tender {}: {}".format(
                response.status_code, tender_id, response.text
            ), task=self, extra={
                "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_UNSUCCESSFUL_CODE",
                "STATUS_CODE": response.status_code
            })
            raise self.retry(countdown=response.headers.get("Retry-After", DEFAULT_RETRY_AFTER))

        tender = response.json()["data"]

        allowed_statuses = ["mistaken", "satisfied", "resolved", "invalid", "stopped", "declined"]

        for complaint_data in tender.get("complaints", []):
            if complaint_data["status"] in allowed_statuses:
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
                    if complaint_data["status"] in allowed_statuses:
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


@app.task(bind=True, max_retries=None)
def process_complaint_params(self, complaint_params, complaint_data):
    try:
        payment = get_payment_item_by_params(complaint_params)
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
        ), task=self, extra={
            "MESSAGE_ID": "PAYMENTS_CRAWLER_PAYMENT_NOT_FOUND"
        })


@app.task(bind=True, max_retries=None)
def process_complaint_resolution(self, payment_data, complaint_data, *args, **kwargs):
    status = complaint_data.get("status")
    reason = complaint_data.get("rejectReason")
    funds = None
    resolution = status

    if status in ["mistaken"]:
        date = complaint_data.get("date")

        if reason in ["incorrectPayment", "complaintPeriodEnded"]:
            funds = "complainant"

    elif status in ["satisfied", "resolved"]:
        resolution = "satisfied"
        date = complaint_data.get("dateDecision")
        funds = "complainant"

    elif status in ["invalid"]:
        date = complaint_data.get("dateDecision")
        if reason in ["buyerViolationsCorrected"]:
            funds = "complainant"
        else:
            funds = "state"

    elif status in ["stopped"]:
        date = complaint_data.get("dateDecision")
        if reason in ["buyerViolationsCorrected"]:
            funds = "complainant"
        else:
            funds = "state"

    elif status in ["declined"]:
        date = complaint_data.get("dateDecision")
        funds = "state"

    else:
        date = complaint_data.get("dateDecision")

    resolution = {
        "date": date,
        "type": resolution,
        "reason": reason,
        "funds": funds,
    }
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
