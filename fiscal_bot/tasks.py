from celery_worker.celery import app
from celery_worker.locks import unique_task_decorator
from celery.utils.log import get_task_logger
from environment_settings import (
    PUBLIC_API_HOST, API_VERSION,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD,
    FISCAL_API_HOST, FISCAL_TEST_MODE, FISCAL_TEST_NAME, FISCAL_TEST_IDENTIFIER
)
from fiscal_bot.settings import (
    IDENTIFICATION_SCHEME, DOC_TYPE,
    WORKING_DAYS_BEFORE_REQUEST_AGAIN, REQUEST_MAX_RETRIES,
)
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER
from fiscal_bot.fiscal_api import build_receipt_request
from tasks_utils.datetime import get_now, get_working_datetime, working_days_count_since
from tasks_utils.tasks import upload_to_doc_service
from tasks_utils.results_db import get_task_result, save_task_result
from tasks_utils.settings import RETRY_REQUESTS_EXCEPTIONS
from datetime import timedelta
import requests
import base64


logger = get_task_logger(__name__)


@app.task(bind=True)
@unique_task_decorator
def process_tender(self, tender_id):
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
        logger.exception(exc, extra={"MESSAGE_ID": "FISCAL_GET_TENDER_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger.error("Unexpected status code {} while getting tender {}: {}".format(
                response.status_code, tender_id, response.text
            ), extra={"MESSAGE_ID": "EDR_GET_TENDER_CODE_ERROR",
                      "STATUS_CODE": response.status_code})
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        tender = response.json()["data"]

        for award in tender.get('awards', []):
            if award["status"] == "pending":
                if not any(doc.get('documentType') == DOC_TYPE for doc in award.get('documents', [])):
                    for supplier in award['suppliers']:
                        identifier = str(supplier['identifier']['id'])

                        if len(identifier) in (8, 10) and supplier['identifier']['scheme'] == IDENTIFICATION_SCHEME:

                            if 'legalName' in supplier['identifier']:
                                name = supplier['identifier']['legalName']
                            else:
                                name = supplier['name']

                            if FISCAL_TEST_MODE:
                                name = FISCAL_TEST_NAME
                                identifier = FISCAL_TEST_IDENTIFIER
                                logger.info(
                                    "FISCAL_TEST_MODE is enabled: {} {}".format(name, identifier),
                                    extra={"MESSAGE_ID": "FISCAL_TEST_MODE"}
                                )

                            prepare_receipt_request.delay(
                                supplier=dict(
                                    tender_id=tender['id'],
                                    tenderID=tender['tenderID'],
                                    award_id=award['id'],
                                    identifier=identifier,
                                    name=name,
                                )
                            )
                        else:
                            logger.warning("Invalid supplier identifier",
                                           extra={"MESSAGE_ID": "FISCAL_IDENTIFIER_VALIDATION_ERROR"})


@app.task(bind=True, max_retries=10)
def prepare_receipt_request(self, supplier, requests_reties=0):
    filename, content = build_receipt_request(self, supplier["tenderID"], supplier["identifier"], supplier["name"])
    try:
        response = requests.post(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (filename, content)},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_ENCODE_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Encrypting has failed: {} {}".format(response.status_code, response.text)
            )
            self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            request_data = base64.b64encode(response.content).decode()
            eta = get_working_datetime(get_now())
            send_request_receipt.apply_async(
                eta=eta,
                kwargs=dict(
                    request_data=request_data,
                    filename=filename,
                    supplier=supplier,
                    requests_reties=requests_reties
                )
            )


@app.task(bind=True, max_retries=10)
def send_request_receipt(self, request_data, filename, supplier, requests_reties):
    task_args = supplier, requests_reties
    data = get_task_result(self, task_args)
    if data is None:
        try:
            response = requests.post(
                '{}/cabinet/public/api/exchange/report'.format(FISCAL_API_HOST),
                json=[{'contentBase64': request_data, 'fname': filename}]
            )
        except RETRY_REQUESTS_EXCEPTIONS as e:
            logger.exception(e, extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_ERROR"})
            raise self.retry(exc=e)
        else:
            if response.status_code != 200:
                logger.error("Unsuccessful status code: {} {}".format(response.status_code, response.text),
                             extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_ERROR"})
                self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
            else:
                data = response.json()

                if data["status"] != "OK":
                    logger.error("Getting receipt failed: {} {}".format(response.status_code, response.text),
                                 extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_ERROR"})
                    return
                else:
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
    # one (if it's working)
    now = get_now()
    check_response_time = get_working_datetime(now + timedelta(seconds=60 * 60))
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


@app.task(bind=True, max_retries=10)
def decode_and_save_data(self, name, data, tender_id, award_id):
    try:
        response = requests.post(
            "{}/decrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (name, base64.b64decode(data))},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_REQUEST_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Signing has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "FISCAL_API_STATUS_ERROR"}
            )
            if response.status_code != 422:
                self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            if response.content.startswith(b"<?xml"):
                upload_to_doc_service.delay(
                    name=name,
                    content=base64.b64encode(response.content).decode(),
                    doc_type=DOC_TYPE,
                    tender_id=tender_id,
                    item_name="award",
                    item_id=award_id
                )
            else:
                logger.error(
                    "Unexpected fiscal data: {}".format(response.status_code, response.text),
                    extra={"MESSAGE_ID": "FISCAL_API_DATA_ERROR"}
                )


@app.task(bind=True, max_retries=10)
def prepare_check_request(self, uid, supplier, request_time, requests_reties):
    """
    :param self:
    :param uid:
    :param supplier:
    :param request_time:
    :param requests_reties: number of request files sent to sfs by send_request_receipt
    :return:
    """
    # encrypt uid
    uid = str(uid)
    try:
        response = requests.post(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (uid, uid.encode())},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_ENCODE_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Encrypting has failed: {} {}".format(response.status_code, response.text)
            )
            self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            check_for_response_file.delay(
                request_data=base64.b64encode(response.content).decode(),
                supplier=supplier,
                request_time=request_time,
                requests_reties=requests_reties,
            )


@app.task(bind=True, max_retries=None)
def check_for_response_file(self, request_data, supplier, request_time, requests_reties):

    if working_days_count_since(request_time) > WORKING_DAYS_BEFORE_REQUEST_AGAIN:

        if requests_reties < REQUEST_MAX_RETRIES:
            prepare_receipt_request.delay(
                supplier=supplier,
                requests_reties=requests_reties + 1
            )
            logger.warning(
                "Request retry scheduled",
                extra={"MESSAGE_ID": "FISCAL_REQUEST_RETRY"}
            )
        else:
            logger.warning(
                "Additional requests number {} exceeded".format(REQUEST_MAX_RETRIES),
                extra={"MESSAGE_ID": "FISCAL_REQUEST_RETRY_EXCEED"}
            )

    else:
        try:
            response = requests.post(
                '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                data=request_data
            )
        except RETRY_REQUESTS_EXCEPTIONS as e:
            logger.exception(e, extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_ERROR"})
            raise self.retry(exc=e)
        else:

            if response.status_code != 200:
                logger.error("Unsuccessful status code: {} {}".format(response.status_code, response.text),
                             extra={"MESSAGE_ID": "FISCAL_API_POST_RESULT_ERROR"})
                self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
            else:
                data = response.json()

                if data.get("status") != "OK" or not any(kv.get("finalKvt") for kv in data.get("kvtList", [])):

                    for kv in data.get("kvtList", []):  # strip file content for logger
                        kv["kvtBase64"] = "{}...".format(kv["kvtBase64"][:10])
                    logger.error("Unsuccessful: {}".format(data),
                                 extra={"MESSAGE_ID": "FISCAL_API_POST_RESULT_UNSUCCESSFUL_RESPONSE"})

                    #  schedule next check on work time
                    eta = get_working_datetime(get_now() + timedelta(seconds=60 * 60))
                    raise self.retry(eta=eta)

                else:
                    for kvt in data["kvtList"]:
                        if kvt["finalKvt"]:
                            decode_and_save_data.delay(
                                kvt["kvtFname"],
                                kvt["kvtBase64"],
                                supplier["tender_id"],
                                supplier["award_id"]
                            )
                            logger.info(
                                "Found kvt file: {}".format(
                                    {k: v for k, v in kvt.items() if k != "kvtBase64"}
                                ),
                                extra={"MESSAGE_ID": "FISCAL_API_POST_RESULT_KVT_NOT_FOUND"}
                            )
