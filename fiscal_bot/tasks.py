from celery_worker.celery import app, formatter
from celery_worker.locks import unique_lock, concurrency_lock
from celery.utils.log import get_task_logger
from environment_settings import (
    PUBLIC_API_HOST, API_VERSION,
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD,
    FISCAL_API_HOST, FISCAL_API_PROXIES, CONNECT_TIMEOUT, READ_TIMEOUT, DEFAULT_RETRY_AFTER,
)
from fiscal_bot.settings import (
    IDENTIFICATION_SCHEME, DOC_TYPE,
    WORKING_DAYS_BEFORE_REQUEST_AGAIN, REQUEST_MAX_RETRIES,
    WORKING_TIME,
    NUMBER_OF_WORKING_DAYS_FOR_REQUEST_RETRY_MAPPING,
)
from fiscal_bot.fiscal_api import build_receipt_request
from fiscal_bot.settings import FISCAL_BOT_START_DATE
from fiscal_bot.utils import (
    save_check_receipt_task_info,
    get_check_receipt_tasks_info_by_tender_id_award_id,
    get_check_receipt_task_info_by_id,
)
from tasks_utils.datetime import get_now, get_working_datetime, working_days_count_since
from tasks_utils.tasks import upload_to_doc_service
from tasks_utils.results_db import get_task_result, save_task_result
from tasks_utils.settings import RETRY_REQUESTS_EXCEPTIONS, DEFAULT_HEADERS
from tasks_utils.requests import (
    get_filename_from_response,
    get_task_retry_logger_method,
    get_exponential_request_retry_countdown,
)
from datetime import timedelta
import requests
import base64


logger = get_task_logger(__name__)


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
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FISCAL_GET_TENDER_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method("Unexpected status code {} while getting tender {}: {}".format(
                response.status_code, tender_id, response.text
            ), extra={
                "MESSAGE_ID": "FISCAL_GET_TENDER_UNSUCCESSFUL_CODE",
                "STATUS_CODE": response.status_code,
            })
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        tender = response.json()["data"]

        for award in tender.get('awards', []):
            if award["status"] == "active" and award["date"] > FISCAL_BOT_START_DATE:
                if not any(doc.get('documentType') == DOC_TYPE for doc in award.get('documents', [])):
                    lot_ids = [l.get("id") for l in tender.get('lots', [])]

                    for supplier in award['suppliers']:
                        identifier = str(supplier['identifier']['id'])

                        if len(identifier) in (8, 10) and supplier['identifier']['scheme'] == IDENTIFICATION_SCHEME:

                            if 'legalName' in supplier['identifier']:
                                name = supplier['identifier']['legalName']
                            else:
                                name = supplier['name']

                            prepare_receipt_request.delay(
                                supplier=dict(
                                    tender_id=tender['id'],
                                    tenderID=tender['tenderID'],
                                    lot_index=lot_ids.index(award['lotID']) if "lotID" in award else None,
                                    award_id=award['id'],
                                    identifier=identifier,
                                    name=name,
                                )
                            )
                        else:
                            logger.warning("Invalid supplier identifier",
                                           extra={"MESSAGE_ID": "FISCAL_IDENTIFIER_VALIDATION_ERROR"})


@app.task(bind=True, max_retries=10)
@concurrency_lock
@unique_lock
def prepare_receipt_request(self, supplier, requests_reties=0):
    filename, content = build_receipt_request(self, supplier["tenderID"], supplier.get("lot_index"),
                                              supplier["identifier"], supplier["name"])
    try:
        response = requests.post(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (filename, content)},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_ENCRYPT_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Encrypting has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "FISCAL_ENCRYPT_API_ERROR"}
            )
            self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            request_data = base64.b64encode(response.content).decode()
            send_request_receipt.apply_async(
                kwargs=dict(
                    request_data=request_data,
                    filename=filename,
                    supplier=supplier,
                    requests_reties=requests_reties
                )
            )


@app.task(bind=True, max_retries=50)
@formatter.omit(["request_data"])
def send_request_receipt(self, request_data, filename, supplier, requests_reties):
    task_args = supplier, requests_reties
    data = get_task_result(self, task_args)
    if data is None:
        try:
            response = requests.post(
                '{}/cabinet/public/api/exchange/report'.format(FISCAL_API_HOST),
                proxies=FISCAL_API_PROXIES,
                json=[{'contentBase64': request_data, 'fname': filename}],
                headers=DEFAULT_HEADERS,
            )
        except RETRY_REQUESTS_EXCEPTIONS as e:
            logger.exception(e, extra={"MESSAGE_ID": "FISCAL_API_POST_REQUEST_ERROR"})
            raise self.retry(exc=e, countdown=get_exponential_request_retry_countdown(self))
        else:
            if response.status_code != 200:
                logger.error("Unsuccessful status code: {} {}".format(response.status_code, response.text),
                             extra={"MESSAGE_ID": "FISCAL_API_POST_INVALID_STATUS_CODE_RESPONSE_ERROR"})
                raise self.retry(countdown=get_exponential_request_retry_countdown(self, response))
            else:
                data = response.json()

                if data["status"] != "OK":
                    if data["status"] != "ERROR_DB":
                        logger.info(
                            "Getting receipt status: {} {}, retrying ...".format(
                                response.status_code, response.text
                            ),
                            extra={"MESSAGE_ID": "FISCAL_API_POST_DATA_STATUS_ERROR_RESPONSE"}
                        )
                        self.retry(
                            countdown=get_exponential_request_retry_countdown(self, response)
                        )
                    else:
                        if "CallableStatementCallback" in data["message"]:
                            logger.error(
                                "Getting receipt failed: {} {}".format(response.status_code, response.text),
                                extra={"MESSAGE_ID": "FISCAL_API_POST_CALLABLE_STATEMENT_CALLBACK_ERROR_RESPONSE"}
                            )
                            self.retry(
                                countdown=get_exponential_request_retry_countdown(self, response)
                            )
                        else:
                            logger.error(
                                "Getting receipt failed: {} {}".format(response.status_code, response.text),
                                extra={"MESSAGE_ID": "FISCAL_API_POST_DATA_STATUS_ERROR_DB_RESPONSE"}
                            )
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


@app.task(bind=True, max_retries=10)
@formatter.omit(["data"])
def decode_and_save_data(self, name, data, tender_id, award_id):
    try:
        response = requests.post(
            "{}/decrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (name, base64.b64decode(data))},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_DECRYPT_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Signing has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "FISCAL_DECRYPT_API_ERROR"}
            )
            if response.status_code != 422:
                self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))
        else:
            filename = get_filename_from_response(response)
            upload_to_doc_service.delay(
                name=filename or name,
                content=base64.b64encode(response.content).decode(),
                doc_type=DOC_TYPE,
                tender_id=tender_id,
                item_name="award",
                item_id=award_id
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
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as e:
        logger.exception(e, extra={"MESSAGE_ID": "FISCAL_ENCRYPT_API_ERROR"})
        raise self.retry(exc=e)
    else:
        if response.status_code != 200:
            logger.error(
                "Encrypting has failed: {} {}".format(response.status_code, response.text),
                extra={"MESSAGE_ID": "FISCAL_ENCRYPT_API_ERROR"}
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
@formatter.omit(["request_data"])
def check_for_response_file(self, request_data, supplier, request_time, requests_reties):
    """"
    * Checking for response file. In case no answer after WORKING_DAYS_BEFORE_REQUEST_AGAIN ->
    called new prepare_receipt_request.
    * If successful response appears in any task with same tenderID -> Stop all check_for_response_file tasks for
     specified tenderID.

    requests_reties / days | 1 2 3 4 5 6 7 8 9 10
    -----------------------|---------------------
    initial task           | + + + + + + + + + +
    1st task               |     + + + + + + + +
    2nd task               |         + + + + + +
    """

    task_id = self.request.id
    tender_id = supplier["tender_id"]
    award_id = supplier["award_id"]
    if self.request.retries == 0:
        save_check_receipt_task_info(tender_id, task_id, award_id)

    tender_check_receipts_tasks = get_check_receipt_tasks_info_by_tender_id_award_id(tender_id, award_id)

    if any([record["receiptFileSuccessfullySaved"] for record in tender_check_receipts_tasks]):
        logger.info(
            "Receipt file for {} tender, {} award has been already obtained by another task. Stop checking.".format(
                tender_id, award_id
            ),
            extra={"MESSAGE_ID": "FISCAL_API_STOP_CHECKING_DUE_TO_ANOTHER_SUCCESSFUL_TASK"}
        )
        return

    try:
        number_of_working_days_for_check = NUMBER_OF_WORKING_DAYS_FOR_REQUEST_RETRY_MAPPING[requests_reties]
    except KeyError:
        logger.error(extra={"MESSAGE_ID": "UNEXPECTED_REQUEST_RETRY_NUMBER"})
        return

    days_passed = working_days_count_since(request_time, working_weekends_enabled=True)
    check_receipt_task_info = get_check_receipt_task_info_by_id(task_id)

    if check_receipt_task_info:
        has_called_new_check_receipt_task = check_receipt_task_info['hasCalledNewCheckReceiptTask']
    else:
        has_called_new_check_receipt_task = False

    if days_passed > WORKING_DAYS_BEFORE_REQUEST_AGAIN:
        if not has_called_new_check_receipt_task:

            if requests_reties < REQUEST_MAX_RETRIES:
                save_check_receipt_task_info(
                    tender_id, task_id, award_id, has_called_new_check_receipt_task=True
                )
                prepare_receipt_request.delay(
                    supplier=supplier,
                    requests_reties=requests_reties + 1
                )
                logger.info(
                    "Request retry scheduled for {} days".format(number_of_working_days_for_check),
                    extra={"MESSAGE_ID": "FISCAL_REQUEST_RETRY_SCHEDULED"}
                )
            else:
                logger.warning(
                    "Additional requests number {} exceeded".format(REQUEST_MAX_RETRIES),
                    extra={"MESSAGE_ID": "FISCAL_REQUEST_RETRY_EXCEED"}
                )

    if days_passed <= number_of_working_days_for_check:
        try:
            response = requests.post(
                '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                proxies=FISCAL_API_PROXIES,
                data=request_data,
                headers=DEFAULT_HEADERS,
            )
        except RETRY_REQUESTS_EXCEPTIONS as e:
            logger.exception(e, extra={"MESSAGE_ID": "FISCAL_API_CHECK_RESPONSE_ERROR"})
            raise self.retry(exc=e)
        else:

            if response.status_code != 200:
                logger.error("Unsuccessful status code: {} {}".format(response.status_code, response.text),
                             extra={"MESSAGE_ID": "FISCAL_API_CHECK_RESPONSE_ERROR"})
                raise self.retry(countdown=get_exponential_request_retry_countdown(self, response))
            else:
                data = response.json()

                kvt_list = data.get("kvtList") or []
                if data.get("status") != "OK" or not any(kv.get("finalKvt") for kv in kvt_list):
                    for kv in kvt_list:  # strip file content for logger
                        if isinstance(kv, dict) and "kvtBase64" in kv:
                            kv["kvtBase64"] = "{}...".format(kv["kvtBase64"][:10])
                    logger.warning("Unsuccessful: {}".format(data),
                                   extra={"MESSAGE_ID": "FISCAL_API_CHECK_UNSUCCESSFUL_RESPONSE"})

                    #  schedule next check on work time
                    eta = get_working_datetime(
                        get_now() + timedelta(seconds=60 * 60),
                        custom_wd=WORKING_TIME,
                        working_weekends_enabled=True,
                    )
                    raise self.retry(eta=eta)

                else:
                    for kvt in data["kvtList"]:
                        if kvt["finalKvt"]:
                            save_check_receipt_task_info(
                                tender_id, task_id, award_id,
                                has_called_new_check_receipt_task=has_called_new_check_receipt_task,
                                receipt_file_successfully_saved=True
                            )

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
                                extra={"MESSAGE_ID": "FISCAL_API_KVT_FOUND"}
                            )
    else:
        logger.warning(
            "{}/{} number of working days exceed for receipt request retry №{}. Stop checking.".format(
                days_passed, number_of_working_days_for_check, requests_reties+1),
            extra={"MESSAGE_ID": "FISCAL_REQUEST_WORKING_DAYS_RETRY_EXCEED"}
        )

