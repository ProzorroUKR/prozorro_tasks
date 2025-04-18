import json

from celery_worker.celery import app, formatter
from celery_worker.locks import unique_lock, concurrency_lock
from celery.utils.log import get_task_logger
from base64 import b64encode
from tasks_utils.requests import (
    get_request_retry_countdown,
    get_exponential_request_retry_countdown,
    get_task_retry_logger_method,
)
from tasks_utils.tasks import upload_to_doc_service
from app.utils import get_cert_base64

from nazk_bot.settings import DOC_TYPE, DOC_NAME, NAZK_NOT_RETRYING_STATUS_CODES
from environment_settings import (
    NAZK_LOG_RESPONSE, PUBLIC_API_HOST, API_VERSION,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD,
    NAZK_API_HOST, NAZK_API_INFO_URI,
    NAZK_PROZORRO_OPEN_CERTIFICATE_NAME,
    CONNECT_TIMEOUT, READ_TIMEOUT,
    DEFAULT_RETRY_AFTER,
)
import requests

from tasks_utils.settings import DEFAULT_HEADERS

logger = get_task_logger(__name__)

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True)
def process_tender(self, tender_id, *args, **kwargs):
    url = "{host}/api/{version}/tenders/{tender_id}".format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        tender_id=tender_id,
    )

    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "NAZK_GET_TENDER_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while getting tender {}".format(
                response.status_code, tender_id
            ), extra={
                "MESSAGE_ID": "NAZK_GET_TENDER_CODE_ERROR",
                "STATUS_CODE": response.status_code,
            })
            raise self.retry(countdown=get_request_retry_countdown(response))

        tender = response.json()["data"]

        if 'awards' in tender:
            for award in tender['awards']:
                if should_process_award(award):
                    for supplier in award['suppliers']:
                        identifier = supplier['identifier']['id']
                        if is_valid_identifier(identifier):
                            prepare_nazk_request.delay(
                                supplier=supplier,
                                tender_id=tender['id'],
                                award_id=award['id'],
                            )
                        else:
                            logger.warning('Tender {} award {} identifier {} is not valid.'.format(
                                tender['id'], award["id"], identifier
                            ), extra={"MESSAGE_ID": "NAZK_INVALID_IDENTIFIER"})


def should_process_award(award):
    return (award['status'] == 'active' and
            not any(document.get('documentType', '') == DOC_TYPE
                    for document in award.get('documents', [])))


def check_related_lot_status(tender, award):
    """Check if related lot not in status cancelled"""
    lot_id = award.get('lotID')
    if lot_id:
        lot_statuses = [
            l['status']
            for l in tender.get('lots', [])
            if l['id'] == lot_id
        ]
        return lot_statuses and 'active' in lot_statuses
    return True


def is_valid_identifier(idf):
    idf = str(idf)
    return (
        (idf.isdigit() and 8 <= len(idf) <= 10)
        or (idf[:2].isalpha() and len(idf[2:]) == 6 and idf[2:].isdigit())
    )


@app.task(bind=True, max_retries=10)
@concurrency_lock
@unique_lock
def prepare_nazk_request(self, supplier, tender_id, award_id):
    identifier = supplier["identifier"]
    code = str(identifier["id"])
    legal_name = identifier.get("legalName", "") or supplier.get("name", "")
    if code.isdigit() and len(code) == 8:
        req_data = {"entityType": "le", "entityRegCode": code, "leFullName": legal_name}
    else:
        req_data = {"entityType": "individual", "entityRegCode": code, "indLastName": legal_name,
                    "indFirstName": "", "indPatronymic": ""}

    try:
        response = requests.post(
            "{}/encrypt_nazk_data".format(API_SIGN_HOST),
            json=req_data,
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "NAZK_ENCRYPT_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Encrypting has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "NAZK_ENCRYPT_API_ERROR"}
            )
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            request_data = b64encode(response.content).decode()
            send_request_nazk.apply_async(
                kwargs=dict(
                    request_data=request_data,
                    tender_id=tender_id,
                    award_id=award_id,
                )
            )


@app.task(bind=True, max_retries=10)
@unique_lock(omit=["request_data"])
@formatter.omit(["request_data"])
def send_request_nazk(self, request_data, tender_id, award_id):
    try:
        cert = get_cert_base64(NAZK_PROZORRO_OPEN_CERTIFICATE_NAME)  # should be in base64
    except FileNotFoundError as e:
        logger.warning(
            '{} file not found'.format(NAZK_PROZORRO_OPEN_CERTIFICATE_NAME),
            extra={"MESSAGE_ID": "NAZK_CERTIFICATE_NOT_FOUND_EXCEPTION"},
        )
        raise e

    try:
        response = requests.post(
            url="{host}/{uri}".format(host=NAZK_API_HOST, uri=NAZK_API_INFO_URI),
            json={"certificate": cert, "data": request_data},
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "NAZK_API_POST_REQUEST_ERROR"})
        raise self.retry(exc=e, countdown=get_exponential_request_retry_countdown(self))
    else:
        if response.status_code != 200:
            logger.error("Unsuccessful status code: {} {}".format(response.status_code, response.text),
                         extra={"MESSAGE_ID": "NAZK_API_POST_INVALID_STATUS_CODE_RESPONSE_ERROR"})
            if response.status_code in NAZK_NOT_RETRYING_STATUS_CODES:
                return
            raise self.retry(countdown=get_exponential_request_retry_countdown(self, response))
        else:
            data = response.text
            logger.info(
                "Nazk requested successfully: {}".format(
                    response.status_code
                ),
                extra={"MESSAGE_ID": "NAZK_API_POST_REQUEST_SUCCESS"}
            )
            if NAZK_LOG_RESPONSE:
                logger.info(
                    "Nazk response: {}".format(data),
                    extra={"MESSAGE_ID": "NAZK_API_POST_RESPONSE"}
                )

    decode_and_save_data.apply_async(
        kwargs=dict(
            data=data,
            tender_id=tender_id,
            award_id=award_id,
        )
    )


@app.task(bind=True, max_retries=10)
@formatter.omit(["data"])
def decode_and_save_data(self, data, tender_id, award_id):
    try:
        response = requests.post(
            url="{}/decrypt_nazk_data".format(API_SIGN_HOST),
            json={"data": data},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "NAZK_DECRYPT_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Signing has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "NAZK_DECRYPT_API_ERROR"}
            )
            if response.status_code != 422:
                self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            data = response.text
            upload_to_doc_service.delay(
                name=DOC_NAME,
                content=data,
                doc_type=DOC_TYPE,
                tender_id=tender_id,
                item_name="award",
                item_id=award_id,
                decode_data=False
            )
