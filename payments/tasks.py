from celery_worker.celery import app
from celery.utils.log import get_task_logger

from payments.utils import (
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    get_complaint_params,
)
from tasks_utils.requests import get_request_retry_countdown
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
from uuid import uuid4
import requests


logger = get_task_logger(__name__)

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(name="payments.process_payment", bind=True)
def process_payment(self, payment_data, *args, **kwargs):
    """
    Process and validate payment data

    :param self:
    :param payment_data: dict

    Example:
    >>> {
    ...     "amount": "123",
    ...     "currency": "UAH",
    ...     "description": "/tenders/6be521090fa444c881e27af026c04e8a/complaints/3a0cc410ab374e2d8a9361dd59436c76"
    ... }

    :param args:
    :param kwargs:
    :return:
    """
    description = payment_data.get("description", "")

    complaint_params = get_complaint_params(description.lower())
    if not complaint_params:
        logger.critical("No valid pattern found for \"{}\"".format(
            payment_data.get("description", "")
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_PATTERN"})
        return
    
    tender_id = complaint_params.get("tender_id")

    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=tender_id
    )

    try:
        response = requests.get(
            url,
            headers={"X-Client-Request-ID": uuid4().hex},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_TENDER_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code == 404:
            logger.critical("No tender found with id {}".format(
                tender_id
            ), extra={"MESSAGE_ID": "PAYMENTS_TENDER_NOT_FOUND"})
            return
        if response.status_code != 200:
            logger.error("Unexpected status code {} while getting tender {}".format(
                response.status_code, tender_id
            ), extra={"MESSAGE_ID": "PAYMENTS_GET_TENDER_CODE_ERROR",
                      "STATUS_CODE": response.status_code})
            raise self.retry(countdown=get_request_retry_countdown(response))
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
                logger.critical("No {} with id {} found in tender {}".format(
                    item_type, item_id,  tender_id
                ), extra={"MESSAGE_ID": "PAYMENTS_ITEM_NOT_FOUND"})
                return
            complaint_data =  get_item_data(item_data, "complaints", complaint_id)
        else:
            complaint_data = get_item_data(tender_data, "complaints", complaint_id)

        if not complaint_data:
            logger.critical("No complaints with id found {} in tender {}".format(
                complaint_id, tender_id
            ), extra={"MESSAGE_ID": "PAYMENTS_COMPLAINT_NOT_FOUND"})
            return

        if not check_complaint_status(complaint_data):
            logger.critical("Complaint status is not valid: {}.".format(
                complaint_data["status"]
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_STATUS"})
            return

        if not check_complaint_value_amount(complaint_data, payment_data):
            logger.critical("Payment amount doesn't match complaint amount ({} and {}) in complaint {}.".format(
                payment_data.get("amount"), complaint_data.get("value", {}).get("amount"), complaint_id
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_AMOUNT"})
            process_complaint.apply_async(
                kwargs=dict(
                    complaint_params=complaint_params,
                    data={
                        "status": "mistaken"
                    }
                )
            )
            return

        if not check_complaint_value_currency(complaint_data, payment_data):
            logger.critical("Payment currency doesn't match complaint currency ({} and {}) in complaint {}.".format(
                payment_data.get("currency"), complaint_data.get("value", {}).get("currency"), complaint_id
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_CURRENCY"})
            process_complaint.apply_async(
                kwargs=dict(
                    complaint_params=complaint_params,
                    data={
                        "status": "mistaken"
                    }
                )
            )
            return

        process_complaint.apply_async(
            kwargs=dict(
                complaint_params=complaint_params,
                data={
                    "status": "pending"
                }
            )
        )


@app.task(bind=True)
def process_complaint(self, complaint_params, data):
    if complaint_params.get("item_type"):
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"

    url = url_pattern.format(
        host=API_HOST,
        version=API_VERSION,
        **complaint_params
    )

    # get SERVER_ID cookie
    try:
        head_response = requests.head(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': uuid4().hex,
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION"})
        raise self.retry(exc=exc)
    else:

        # patch complaint
        try:
            response = requests.patch(
                url,
                json={'data': data},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': uuid4().hex,
                },
                cookies=head_response.cookies,
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_EXCEPTION"})
            raise self.retry(exc=exc)
        else:
            complaint_id = complaint_params.get("complaint_id")
            tender_id = complaint_params.get("tender_id")

            # handle response code
            if response.status_code == 422:
                logger.error("Incorrect data while patching complaint {} of tender {}: {}".format(
                    complaint_id, tender_id, response.text
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_DATA_ERROR"})
                return

            elif response.status_code == 403:
                logger.error("Forbidden while patching complaint {} of tender {}: {}".format(
                    complaint_id, tender_id, response.text
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_FORBIDDEN_ERROR"})

            elif response.status_code != 200:
                logger.error("Unexpected status code {} while patching complaint {} of tender {}: {}".format(
                    response.status_code, complaint_id, tender_id, data
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_CODE_ERROR",
                          "STATUS_CODE": response.status_code})
                raise self.retry(countdown=get_request_retry_countdown(response))
            else:
                logger.info("Successfully updated complaint {} of tender {}: {}".format(
                    complaint_id, tender_id, data
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_SUCCESS"})
