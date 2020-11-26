from celery_worker.celery import app, formatter
from celery_worker.locks import unique_lock, concurrency_lock
from celery.utils.log import get_task_logger
from tasks_utils.requests import (
    get_request_retry_countdown,
    get_exponential_request_retry_countdown,
    get_task_retry_logger_method,
)
from tasks_utils.settings import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
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
from environment_settings import (
    API_HOST, API_TOKEN, PUBLIC_API_HOST, API_VERSION,
    EDR_API_HOST, EDR_API_PORT, EDR_API_VERSION, EDR_API_USER, EDR_API_PASSWORD,
    DS_HOST, DS_USER, DS_PASSWORD,
    SPREAD_TENDER_TASKS_INTERVAL,
)
from uuid import uuid4
import requests
import json
import yaml
import io

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
            headers={"X-Client-Request-ID": uuid4().hex},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_GET_TENDER_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while getting tender {}".format(
                response.status_code, tender_id
            ), extra={
                "MESSAGE_ID": "EDR_GET_TENDER_CODE_ERROR",
                "STATUS_CODE": response.status_code,
            })
            raise self.retry(countdown=get_request_retry_countdown(response))

        tender_data = response.json()["data"]

        if not should_process_tender(tender_data):
            return

        # --------
        i = 0  # spread in time tasks that belongs to a single tender CS-3854
        if 'awards' in tender_data:
            for award in tender_data['awards']:
                if should_process_item(award):
                    for supplier in award['suppliers']:
                        process_award_supplier(response, tender_data, award, supplier, i)
                        i += 1

        elif 'qualifications' in tender_data:
            for qualification in tender_data['qualifications']:
                if should_process_item(qualification):
                    process_qualification(response, tender_data, qualification, i)
                    i += 1


def process_award_supplier(response, tender, award, supplier, item_number):
    if not is_valid_identifier(supplier['identifier']):
        logger.warning('Tender {} award {} identifier {} is not valid.'.format(
            tender['id'], award["id"], supplier['identifier']
        ), extra={"MESSAGE_ID": "EDR_INVALID_IDENTIFIER"})
    elif not check_related_lot_status(tender, award):
        logger.warning("Tender {} bid {} award {} related lot has been cancelled".format(
            tender['id'], award['bid_id'], award['id']
        ), extra={"MESSAGE_ID": "EDR_CANCELLED_LOT"})
    else:
        get_edr_data.apply_async(
            countdown=SPREAD_TENDER_TASKS_INTERVAL * item_number,
            kwargs=dict(
                code=str(supplier['identifier']['id']),
                tender_id=tender['id'],
                item_name="award",
                item_id=award['id']
            )
        )


def process_qualification(response, tender, qualification, item_number):
    appropriate_bids = [b for b in tender.get("bids", [])
                        if b['id'] == qualification['bidID']]
    if not appropriate_bids:
        logger.warning('Tender {} bid {} is missed.'.format(
            tender['id'], qualification['bidID']
        ), extra={"MESSAGE_ID": "EDR_BID_ID_INVALID"})
        return

    tenderers = appropriate_bids[0].get('tenderers')
    if not tenderers:
        logger.warning('Tender {} bid {} tenderers are missed.'.format(
            tender['id'], appropriate_bids[0]['id']
        ), extra={"MESSAGE_ID": "EDR_TENDERER_KEY_MISSED"})
        return

    if not is_valid_identifier(tenderers[0]['identifier']):
        logger.warning('Tender {} qualification {} identifier {} is not valid.'.format(
            tender['id'], qualification["id"], tenderers[0]['identifier']
        ), extra={"MESSAGE_ID": "EDR_INVALID_IDENTIFIER"})
    else:
        get_edr_data.apply_async(
            countdown=SPREAD_TENDER_TASKS_INTERVAL * item_number,
            kwargs=dict(
                code=str(tenderers[0]['identifier']['id']),
                tender_id=tender['id'],
                item_name="qualification",
                item_id=qualification['id']
            )
        )


def should_process_tender(tender):
    if (
        tender['procurementMethodType'] == "reporting" and
        tender.get('procurementMethodRationale') != "COVID-19"
    ):
        return False
    return True


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
    return str(identifier["id"]).isdigit() and identifier['scheme'] == IDENTIFICATION_SCHEME


# ------- GET EDR DATA
@app.task(bind=True, max_retries=20)
@concurrency_lock
@unique_lock
def get_edr_data(self, code, tender_id, item_name, item_id, request_id=None):
    """
    request_id: is deprecated, should be removed in the next releases
    """
    meta = {
        'id': uuid4().hex,
        'author': DOC_AUTHOR,
        'sourceRequests': [],
        'version': EDR_BOT_VERSION,
    }
    param = 'id' if code.isdigit() and len(code) != ID_PASSPORT_LEN else 'passport'
    url = "{host}:{port}/api/{version}/verify?{param}={code}".format(
        host=EDR_API_HOST, port=EDR_API_PORT, version=EDR_API_VERSION,
        param=param,
        code=code,
    )
    try:
        response = requests.get(
            url,
            auth=(EDR_API_USER, EDR_API_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={"X-Client-Request-ID": meta["id"]}
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_GET_DATA_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        meta['sourceRequests'].append(response.headers.get('X-Request-ID', ''))

        try:
            resp_json = response.json()
        except json.decoder.JSONDecodeError as exc:
            logger.warning(
                "JSONDecodeError on edr request with status {}: ".format(response.status_code),
                extra={"MESSAGE_ID": "EDR_JSON_DECODE_EXCEPTION"}
            )
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(exc=exc, countdown=countdown)

        data_list = []

        if (response.status_code == 404 and isinstance(resp_json, dict)
            and len(resp_json.get('errors', "")) > 0 and len(resp_json.get('errors')[0].get('description', '')) > 0
            and resp_json.get('errors')[0].get('description')[0].get('error', {}).get('code', '') == u"notFound"):
            logger.warning('Empty response for {} code {}={}.'.format(tender_id, param, code),
                           extra={"MESSAGE_ID": "EDR_GET_DATA_EMPTY_RESPONSE"})

            file_content = resp_json.get('errors')[0].get('description')[0]
            file_content['meta'].update(meta)
            data_list.append(file_content)

        elif response.status_code == 200:
            document_id = meta["id"]
            for i, obj in enumerate(resp_json['data']):

                if len(resp_json['data']) > 1:
                    meta_id = '{}.{}.{}'.format(document_id, len(resp_json['data']), i + 1)
                else:
                    meta_id = document_id

                source_date = None
                if len(resp_json['meta']['detailsSourceDate']) >= i + 1:
                    source_date = resp_json['meta']['detailsSourceDate'][i]

                file_content = {
                    'meta': {
                        'sourceDate': source_date
                    },
                    'data': obj
                }
                file_content['meta'].update(meta)
                file_content['meta']['id'] = meta_id
                data_list.append(file_content)
        else:
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)

        for data in data_list:
            upload_to_doc_service.delay(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)


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
                headers={'X-Client-Request-ID': data['meta']['id']}
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "EDR_POST_DOC_EXCEPTION"})
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
            }
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_ATTACH_DOC_HEAD_EXCEPTION"})
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
                },
                cookies=head_response.cookies,
            )
        except RETRY_REQUESTS_EXCEPTIONS as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "EDR_ATTACH_DOC_POST_EXCEPTION"})
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
