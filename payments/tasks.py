from celery_worker.celery import app
from celery.utils.log import get_task_logger

from payments.settings import (
    TENDER_COMPLAINT_TYPE,
    QUALIFICATION_COMPLAINT_TYPE,
    AWARD_COMPLAINT_TYPE,
    CANCELLATION_COMPLAINT_TYPE,
)
from payments.utils import (
    get_item_data,
    check_complaint_status,
    check_complaint_value_amount,
    check_complaint_value_currency,
    get_complaint_type,
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

    complaint_type = get_complaint_type(description.lower())
    if not complaint_type:
        logger.critical("No valid pattern found for \"{}\"".format(
            payment_data.get("description", "")
        ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_PATTERN"})
        return

    complaint_params = get_complaint_params(description.lower(), complaint_type)

    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=complaint_params.get("tender_id")
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
            logger.critical("No tender {} for complaint {} found".format(
                complaint_params.get("tender_id"), complaint_params.get("complaint_id")
            ), extra={"MESSAGE_ID": "PAYMENTS_TENDER_NOT_FOUND"})
            return
        if response.status_code != 200:
            logger.error("Unexpected status code {} while getting tender {} for complaint {}".format(
                response.status_code, complaint_params.get("tender_id"), complaint_params.get("complaint_id")
            ), extra={"MESSAGE_ID": "PAYMENTS_GET_TENDER_CODE_ERROR",
                      "STATUS_CODE": response.status_code})
            raise self.retry(countdown=get_request_retry_countdown(response))
        else:
            logger.info("Successfully retrieved tender {} for complaint {}".format(
                complaint_params.get("tender_id"), complaint_params.get("complaint_id")
            ), extra={"MESSAGE_ID": "PAYMENTS_GET_TENDER_SUCCESS"})

        tender_data = response.json()["data"]

        if complaint_type == TENDER_COMPLAINT_TYPE:
            complaint_data = get_item_data(tender_data, "complaints", complaint_params["complaint_id"])

        elif complaint_type == QUALIFICATION_COMPLAINT_TYPE:
            qualification_data =  get_item_data(tender_data, "qualifications", complaint_params["qualification_id"])
            if not qualification_data:
                logger.critical("No qualification {} in tender {} found".format(
                    complaint_params.get("qualification_id"), complaint_params.get("tender_id")
                ), extra={"MESSAGE_ID": "PAYMENTS_QUALIFICATION_NOT_FOUND"})
                return
            complaint_data =  get_item_data(qualification_data, "complaints", complaint_params["complaint_id"])

        elif complaint_type == AWARD_COMPLAINT_TYPE:
            award_data =  get_item_data(tender_data, "awards", complaint_params["award_id"])
            if not award_data:
                logger.critical("No award {} in tender {} found".format(
                    complaint_params.get("award_id"), complaint_params.get("tender_id")
                ), extra={"MESSAGE_ID": "PAYMENTS_AWARD_NOT_FOUND"})
                return
            complaint_data =  get_item_data(award_data, "complaints", complaint_params["complaint_id"])

        elif complaint_type == CANCELLATION_COMPLAINT_TYPE:
            cancellation_data =  get_item_data(tender_data, "cancellations", complaint_params["cancellation_id"])
            if not cancellation_data:
                logger.critical("No cancellation {} in tender {} found".format(
                    complaint_params.get("cancellation_id"), complaint_params.get("tender_id")
                ), extra={"MESSAGE_ID": "PAYMENTS_CANCELLATION_NOT_FOUND"})
                return
            complaint_data =  get_item_data(cancellation_data, "complaints", complaint_params["complaint_id"])

        else:  # pragma: no cover
            raise NotImplementedError()

        if not complaint_data:
            logger.critical("No complaint {} in tender {} found".format(
                complaint_params.get("complaint_id"), complaint_params.get("tender_id")
            ), extra={"MESSAGE_ID": "PAYMENTS_COMPLAINT_NOT_FOUND"})
            return

        if not check_complaint_status(complaint_data):
            logger.critical("Complaint status is not valid :{}.".format(
                complaint_data["status"]
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_STATUS"})
            return

        if not check_complaint_value_amount(complaint_data, payment_data):
            logger.critical("Payment amount not found or doesn't match complaint amount ({} and {}).".format(
                payment_data.get("amount"), complaint_data.get("value", {}).get("amount")
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_AMOUNT"})
            process_complaint.apply_async(
                kwargs=dict(
                    complaint_type=complaint_type,
                    complaint_params=complaint_params,
                    data={
                        "status": "mistaken"
                    }
                )
            )
            return

        if not check_complaint_value_currency(complaint_data, payment_data):
            logger.critical("Payment currency not found or doesn't match complaint currency ({} and {}).".format(
                payment_data.get("currency"), complaint_data.get("value", {}).get("currency")
            ), extra={"MESSAGE_ID": "PAYMENTS_INVALID_CURRENCY"})
            process_complaint.apply_async(
                kwargs=dict(
                    complaint_type=complaint_type,
                    complaint_params=complaint_params,
                    data={
                        "status": "mistaken"
                    }
                )
            )
            return

        process_complaint.apply_async(
            kwargs=dict(
                complaint_type=complaint_type,
                complaint_params=complaint_params,
                data={
                    "status": "pending"
                }
            )
        )


@app.task(bind=True)
def process_complaint(self, complaint_type, complaint_params, data):
    if complaint_type == TENDER_COMPLAINT_TYPE:
        pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"
    elif complaint_type == QUALIFICATION_COMPLAINT_TYPE:
        pattern = "{host}/api/{version}/tenders/{tender_id}/qualifications/{qualification_id}/complaints/{complaint_id}"
    elif complaint_type == AWARD_COMPLAINT_TYPE:
        pattern = "{host}/api/{version}/tenders/{tender_id}/awards/{award_id}/complaints/{complaint_id}"
    elif complaint_type == CANCELLATION_COMPLAINT_TYPE:
        pattern = "{host}/api/{version}/tenders/{tender_id}/cancellations/{cancellation_id}/complaints/{complaint_id}"
    else:  # pragma: no cover
        raise NotImplementedError()

    url = pattern.format(
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
            # handle response code
            if response.status_code == 422:
                logger.error("Incorrect data while patching complaint {} of tender {}: {}".format(
                    complaint_params.get("complaint_id"),
                    complaint_params.get("tender_id"),
                    response.text
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_DATA_ERROR"})

            elif response.status_code == 403:
                logger.error("Forbidden while patching complaint {} of tender {}: {}".format(
                    complaint_params.get("complaint_id"),
                    complaint_params.get("tender_id"),
                    response.text
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_FORBIDDEN_ERROR"})

            elif response.status_code != 200:
                logger.error("Unexpected status code {} while patching complaint {} of tender {}: {}".format(
                    response.status_code,
                    complaint_params.get("complaint_id"),
                    complaint_params.get("tender_id"),
                    data
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_CODE_ERROR",
                          "STATUS_CODE": response.status_code})
                raise self.retry(countdown=get_request_retry_countdown(response))
            else:
                logger.info("Successfully updated complaint {} of tender {}: {}".format(
                    complaint_params.get("complaint_id"),
                    complaint_params.get("tender_id"),
                    data
                ), extra={"MESSAGE_ID": "PAYMENTS_PATCH_COMPLAINT_SUCCESS"})
