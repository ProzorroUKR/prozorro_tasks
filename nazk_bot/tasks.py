from celery_worker.celery import app, formatter
from celery_worker.locks import unique_lock, concurrency_lock
from celery.utils.log import get_task_logger
from base64 import b64encode, b64decode
from tasks_utils.requests import (
    get_request_retry_countdown,
    get_exponential_request_retry_countdown,
    get_task_retry_logger_method,
)
from edr_bot.settings import (
    DOC_TYPE, IDENTIFICATION_SCHEME, DOC_AUTHOR,
    VERSION as EDR_BOT_VERSION,
    FILE_NAME, ID_PASSPORT_LEN,
)
from edr_bot.results_db import (
    get_upload_results,
    save_upload_results,
    set_upload_results_attached,
)
from nazk_bot.api.controllers import get_entity_data_from_nazk, get_base64_prozorro_open_cert
from nazk_bot.api.exceptions import NAZKRequestErrorException
from environment_settings import (
    API_HOST, API_TOKEN, PUBLIC_API_HOST, API_VERSION,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD,
    NAZK_API_HOST, NAZK_API_VERSION,
    DS_HOST, DS_USER, DS_PASSWORD,
    SPREAD_TENDER_TASKS_INTERVAL, CONNECT_TIMEOUT, READ_TIMEOUT,
    DEFAULT_RETRY_AFTER,
)
from uuid import uuid4
import requests
import json
import yaml
import io

from tasks_utils.settings import DEFAULT_HEADERS
from tasks_utils.tasks import ATTACH_DOC_MAX_RETRIES

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
            headers={
                "X-Client-Request-ID": uuid4().hex,
                **DEFAULT_HEADERS,
            },
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

        tender_data = response.json()["data"]

        # --------
        i = 0  # spread in time tasks that belongs to a single tender CS-3854
        if 'awards' in tender_data:
            for award in tender_data['awards']:
                if should_process_item(award):
                    for supplier in award['suppliers']:
                        process_award_supplier(response, tender_data, award, supplier, i)
                        i += 1


def process_award_supplier(response, tender, award, supplier, item_number):
    if not is_valid_identifier(supplier['identifier']):
        logger.warning('Tender {} award {} identifier {} is not valid.'.format(
            tender['id'], award["id"], supplier['identifier']
        ), extra={"MESSAGE_ID": "NAZK_INVALID_IDENTIFIER"})
    elif not check_related_lot_status(tender, award):
        logger.warning("Tender {} bid {} award {} related lot has been cancelled".format(
            tender['id'], award['bid_id'], award['id']
        ), extra={"MESSAGE_ID": "NAZK_CANCELLED_LOT"})
    else:
        get_nazk_data.apply_async(
            countdown=SPREAD_TENDER_TASKS_INTERVAL * item_number,
            kwargs=dict(
                identifier=supplier['identifier'],
                tender_id=tender['id'],
                item_name="award",
                item_id=award['id']
            )
        )


def should_process_item(item):
    return (item['status'] == 'pending' and
            not any(document.get('documentType') == DOC_TYPE
                    for document in item.get('documents', [])))


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


def is_valid_identifier(identifier):
    idf = str(identifier["id"])
    return (
        (idf.isdigit() and 8 <= len(idf) <= 10)
        or (idf[:2].isalpha() and len(idf[2:]) == 6 and idf[2:].isdigit())
    )


@app.task(bind=True, max_retries=10)
@concurrency_lock
@unique_lock
def prepare_nazk_request(self, supplier, requests_reties=0):
    identifier = supplier["identifier"]
    code = str(identifier["id"])
    legal_name = identifier["legalName"]
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
            self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            request_data = b64encode(response.content).decode()
            send_request_nazk.apply_async(
                kwargs=dict(
                    request_data=request_data,
                    supplier=supplier,
                    requests_reties=requests_reties
                )
            )


@app.task(bind=True, max_retries=50)
@formatter.omit(["request_data"])
def send_request_nazk(self, request_data, supplier, requests_reties):
    cert = get_base64_prozorro_open_cert()
    try:
        response = requests.post(
            url="{host}/ep_test/{version}/corrupt/getEntityInfo".format(host=NAZK_API_HOST, version=NAZK_API_VERSION),
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
            raise self.retry(countdown=get_exponential_request_retry_countdown(self, response))
        else:
            data = response.json()

            uid = save_task_result(self, data, task_args)
            logger.info(
                "Receipt requested successfully: {} {} {}; saved result: {}".format(
                    response.status_code, data["id"], data["kvt1Fname"], uid
                ),
                extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_SUCCESS"}
            )

    decode_and_save_data.apply_async(
        kwargs=dict(
            name=data["kvt1Fname"],
            data=data["kvt1Base64"],
            tender_id=supplier["tender_id"],
            award_id=supplier["award_id"],
        )
    )

    # response check should be after an hour
    # also later we will need to know how many working days have passed since now including this
    # one (if it's a working day)
    now = get_now()
    check_response_time = get_working_datetime(
        now + timedelta(seconds=60 * 60),
        custom_wd=WORKING_TIME,
        working_weekends_enabled=True
    )
    prepare_check_request.apply_async(
        eta=check_response_time,
        kwargs=dict(
            uid=data["id"],
            supplier=supplier,
            request_time=now,
            requests_reties=requests_reties,
        )
    )

    logger.info(
        "Fiscal receipt check of {} scheduled at {}".format(
            data["id"], check_response_time
        ),
        extra={"MESSAGE_ID": "FISCAL_API_CHECK_SCHEDULE"}
    )

# ------- GET NAZK DATA
@app.task(bind=True, max_retries=20)
@concurrency_lock
@unique_lock
def get_nazk_data(self, identifier, tender_id, item_name, item_id, request_id=None):
    """
    request_id: is deprecated, should be removed in the next releases
    """
    meta = {
        'id': uuid4().hex,
        'author': DOC_AUTHOR,
        'sourceRequests': [],
        'version': EDR_BOT_VERSION,
    }
    code = str(identifier["id"])
    legal_name = identifier["legalName"]
    if code.isdigit() and len(code) == 8:
        req_data = {"entityType": "le", "entityRegCode": code, "leFullName": legal_name}
    else:
        req_data = {"entityType": "individual", "entityRegCode": code, "indLastName": legal_name,
                    "indFirstName": "", "indPatronymic": ""}

    try:
        entity_data = get_entity_data_from_nazk(req_data)
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "NAZK_GET_DATA_EXCEPTION"})
        raise self.retry(exc=exc)
    except NAZKRequestErrorException as exc:
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown)

    # TODO: should be some operations with entity_data
    # TODO: also maybe upload create and upload document


# --------- UPLOAD TO DS
@app.task(bind=True)
@formatter.omit(["data"])
def upload_to_doc_service(self, data, tender_id, item_name, item_id):
    # check if the file has been already uploaded
    # will retry the task until mongodb returns either doc or None
    unique_data = {k: v for k, v in data.items() if k != "meta"}
    upload_results = get_upload_results(self, unique_data, tender_id, item_name, item_id)

    if upload_results is None:
        # generate file data
        contents = yaml.safe_dump(data, allow_unicode=True, default_flow_style=False)
        temporary_file = io.StringIO(contents)
        temporary_file.name = FILE_NAME

        files = {'file': (FILE_NAME, temporary_file, 'application/yaml')}

        try:
            response = requests.post(
                '{host}/upload'.format(host=DS_HOST),
                auth=(DS_USER, DS_PASSWORD),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                files=files,
                headers={
                    'X-Client-Request-ID': data['meta']['id'],
                    **DEFAULT_HEADERS,
                }
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "NAZK_POST_DOC_EXCEPTION"})
            raise self.retry(exc=exc)
        else:
            if response.status_code != 200:
                logger_method = get_task_retry_logger_method(self, logger)
                logger_method(
                    "Incorrect upload status for doc {}".format(data['meta']['id']),
                    extra={
                        "MESSAGE_ID": "EDR_POST_DOC_ERROR",
                        "STATUS_CODE": response.status_code,
                    })
                raise self.retry(countdown=get_request_retry_countdown(response))

            response_json = response.json()
            response_json['meta'] = {'id': data['meta']['id']}
        # save response to mongodb, so that the file won't be uploaded again
        # fail silently: if mongodb isn't available, the task will neither fail nor retry
        # in worst case there might be a duplicate attached to the tender
        uid = save_upload_results(response_json, unique_data, tender_id, item_name, item_id)
        logger.info("Saved document with uid {} for {} {} {}".format(
            uid, tender_id, item_name, item_id),
            extra={"MESSAGE_ID": "EDR_POST_UPLOAD_RESULTS_SUCCESS"}
        )
    else:
        # we don't need to pass the response since it's saved to mongodb doc
        response_json = None

    attach_doc_to_tender.delay(file_data=response_json,
                               data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)


# ---------- ATTACH DOCUMENT TO ITS TENDER
@app.task(bind=True, max_retries=ATTACH_DOC_MAX_RETRIES)
@formatter.omit(["data"])
def attach_doc_to_tender(self, file_data, data, tender_id, item_name, item_id):
    unique_data = {k: v for k, v in data.items() if k != "meta"}
    upload_results = get_upload_results(self, unique_data, tender_id, item_name, item_id)
    if file_data is None:
        if upload_results is None:
            fall_msg = "Saved results are missed for {} {} {}".format(tender_id, item_name, item_id)
            logger.critical(fall_msg, extra={"MESSAGE_ID": "EDR_SAVED_RESULTS_MISSED"})
            raise AssertionError(fall_msg)
        else:
            file_data = upload_results["file_data"]

    if upload_results and upload_results.get("attached"):
        logger.info("Uploaded file has been already attached to the tender: {} {} {}".format(
            tender_id, item_name, item_id), extra={"MESSAGE_ID": "EDR_FILE_ALREADY_ATTACHED"})
        return

    document_data = file_data['data']
    document_data["documentType"] = DOC_TYPE
    url = "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
        host=API_HOST,
        version=API_VERSION,
        item_name=item_name,
        item_id=item_id,
        tender_id=tender_id,
    )

    meta_id = file_data['meta']['id']
    # get SERVER_ID cookie
    try:
        head_response = requests.head(
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': meta_id,
                **DEFAULT_HEADERS,
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "NAZK_ATTACH_DOC_HEAD_EXCEPTION"})
        raise self.retry(exc=exc)
    else:

        # post document
        try:
            response = requests.post(
                url,
                json={'data': document_data},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                headers={
                    'Authorization': 'Bearer {}'.format(API_TOKEN),
                    'X-Client-Request-ID': meta_id,
                    **DEFAULT_HEADERS,
                },
                cookies=head_response.cookies,
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "NAZK_ATTACH_DOC_POST_EXCEPTION"})
            raise self.retry(exc=exc)
        else:
            # handle response code
            if response.status_code == 422:
                logger.error("Incorrect document data while attaching doc {} to tender {}: {}".format(
                    meta_id, tender_id, response.text
                ), extra={"MESSAGE_ID": "EDR_ATTACH_DATA_ERROR"})

            elif response.status_code != 201:
                logger.warning("Incorrect upload status while attaching doc {} to tender {}".format(
                    meta_id, tender_id
                ), extra={
                    "MESSAGE_ID": "EDR_ATTACH_STATUS_ERROR",
                    "STATUS_CODE": response.status_code,
                })
                raise self.retry(countdown=get_request_retry_countdown(response))
            else:
                # won't raise anything
                uid = set_upload_results_attached(unique_data, tender_id, item_name, item_id)
                logger.info("Set attached document with uid {} for {} {} {}".format(
                    uid, tender_id, item_name, item_id),
                    extra={"MESSAGE_ID": "EDR_SET_ATTACHED_RESULTS"}
                )
