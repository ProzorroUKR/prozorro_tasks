import requests

from uuid import uuid4

from pymongo.errors import PyMongoError

from celery_worker.celery import app, formatter
from celery.utils.log import get_task_logger

from payments.health import health, save_health_data
from payments.logging import PaymentResultsLoggerAdapter
from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
)
from payments.results_db import (
    set_payment_resolution,
    get_payment_item_by_params,
)
from payments.utils import (
    ALLOWED_COMPLAINT_RESOLUTION_STATUSES,
    request_cdb_tender_data,
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


@app.task(bind=True, max_retries=1000)
def process_tender(self, tender_id, *args, **kwargs):
    client_request_id = uuid4().hex
    try:
        response = request_cdb_tender_data(
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
@formatter.omit(["complaint_data"])
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
@formatter.omit(["complaint_data"])
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



@app.task(bind=True, max_retries=10)
def check_payments_status(self):
    data = health()
    save_health_data(data)
