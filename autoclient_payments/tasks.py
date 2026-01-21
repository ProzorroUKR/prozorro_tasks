from datetime import datetime, timedelta
from uuid import uuid4

import requests
from celery.utils.log import get_task_logger
from pymongo.errors import PyMongoError
from kombu.exceptions import OperationalError

from autoclient_payments.enums import TransactionType, TransactionKind, TransactionStatus
from autoclient_payments.health import health, save_health_data
from celery_worker.celery import app, formatter
from autoclient_payments.data import STATUS_COMPLAINT_MISTAKEN, STATUS_COMPLAINT_PENDING
from autoclient_payments.logging import PaymentResultsLoggerAdapter
from autoclient_payments.message_ids import (
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_SEARCH_FAILED,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_SUCCESS,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_SEARCH_VALID_CODE,
    PAYMENTS_GET_COMPLAINT_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_CODE_ERROR,
    PAYMENTS_GET_COMPLAINT_SUCCESS,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_VALID_PAYMENT,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
    PAYMENTS_PB_GET_TRANSACTIONS_EXCEPTION,
)
from autoclient_payments.results_db import (
    set_payment_params,
    set_payment_complaint_author,
    save_payment_item,
    get_last_transaction,
    get_payment_item_by_params,
    set_payment_resolution,
)
from autoclient_payments.utils import (
    get_payment_params,
    request_cdb_complaint_search,
    request_cdb_complaint_data,
    request_cdb_complaint_patch,
    check_complaint_code,
    check_complaint_status,
    check_complaint_value,
    check_complaint_value_amount,
    check_complaint_value_currency,
    PB_DATA_DATE_FORMAT,
    PB_QUERY_DATE_FORMAT,
    ALLOWED_COMPLAINT_RESOLUTION_STATUSES,
    get_resolution,
    request_cdb_tender_data,
    transactions_list,
)
from environment_settings import AUTOCLIENT_PROCESSING_ENABLED
from tasks_utils.datetime import get_now
from tasks_utils.requests import get_exponential_request_retry_countdown, get_task_retry_logger_method

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
    requests.exceptions.HTTPError,
)

COMPLAINT_NOT_FOUND_MAX_RETRIES = 20


def save_and_process_payment(transaction: dict, user: str):
    extra = {"PAYMENT_DESCRIPTION": transaction["OSND"]}
    created_obj = None
    try:
        created_obj = save_payment_item(transaction, user)
    except PyMongoError:
        logger.error("Payment save failed.", extra=extra)
    # process only credit transactions
    if AUTOCLIENT_PROCESSING_ENABLED and created_obj and transaction["TRANTYPE"] == TransactionType.CREDIT.value:
        try:
            process_payment_data.apply_async(kwargs=dict(payment_data=transaction))
        except OperationalError:
            logger.error("Payment send task failed.", extra=extra)


@app.task(bind=True, max_retries=10)
def sync_autoclient_payments(self):
    if last_payment := get_last_transaction():
        last_date = datetime.strptime(last_payment["payment"]["DAT_OD"], PB_DATA_DATE_FORMAT).date()
    else:
        last_date = get_now().date()
    sync_start_date = (last_date - timedelta(days=1)).strftime(PB_QUERY_DATE_FORMAT)

    try:
        for transaction in transactions_list(sync_start_date):
            # save and process only real, recorded transactions
            if (
                transaction["FL_REAL"] == TransactionKind.REAL.value
                and transaction["PR_PR"] == TransactionStatus.RECORDED.value
            ):
                save_and_process_payment(transaction, "system")
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception(
            str(exc),
            extra={
                "MESSAGE_ID": PAYMENTS_PB_GET_TRANSACTIONS_EXCEPTION,
            },
        )
        raise self.retry(countdown=countdown, exc=exc)


@app.task(bind=True, max_retries=1000)
def process_payment_data(self, payment_data, *args, **kwargs):
    """
    Process and validate payment data

    :param self:
    :param payment_data: dict

    Example:
    >>> {
      "AUT_MY_CRF": "31451288", // ЄДРПОУ одержувача
      "AUT_MY_MFO": "305299", // МФО одержувача
      "AUT_MY_ACC": "26184050001514", // рахунок одержувача
      "AUT_MY_NAM": "Програмiсти та Ko МСБ-ТЕСТ ТОВ", // назва одержувача
      "AUT_MY_MFO_NAME": "АТ КБ \"ПРИВАТБАНК\"", // банк одержувача
      "AUT_MY_MFO_CITY": "Київ", // назва міста банку
      "AUT_CNTR_CRF": "14360570", // ЄДРПОУ контрагента
      "AUT_CNTR_MFO": "305299", // МФО контрагента
      "AUT_CNTR_ACC": "70214924104032", // рахунок контрагента
      "AUT_CNTR_NAM": "ПРОЦ ВИТР ЗА СТРОК КОШТ СУБ(UAH)", // назва контрагента
      "AUT_CNTR_MFO_NAME": "АТ КБ \"ПРИВАТБАНК\"", // назва банку контрагента
      "AUT_CNTR_MFO_CITY": "Київ", // назва міста банку
      "CCY": "UAH", // валюта
      "FL_REAL": "r", // ознака реальності проведення (r,i)
      "PR_PR": "r", // стан p - проводиться, t - сторнована, r - проведена, n - забракована
      "DOC_TYP": "m", // тип пл. документа
      "NUM_DOC": "K0108B1WKX", // номер документа
      "DAT_KL": "07.01.2020", // клієнтська дата
      "DAT_OD": "07.01.2020", // дата валютування
      "OSND": "Нарахування вiдсоткiв згiдно депозитного договору N...", // підстава  платежу
      "SUM": "0.01", // сума
      "SUM_E": "0.01", // сума в національній валюті (грн)
      "REF": "DNCHK0108B1WKX", // референс проведення
      "REFN": "1", // № з/п всередині проведення
      "TIM_P": "02:58", // час проведення
      "DATE_TIME_DAT_OD_TIM_P": "07.01.2020 02:58:00",
      "ID": "557091731", // ID транзакції
      "TRANTYPE": "C", // тип транзакції дебет/кредит (D, C)
      "DLR": "J63DNDSM0XHY5", // референс платежу сервісу, через який створювали платіж (payment_pack_ref - у разі створення платежу через АPI «Автоклієнт»)
      "TECHNICAL_TRANSACTION_ID": "557091731_online"
    }

    :return:
    """
    description = payment_data.get("OSND", "")
    payment_params = get_payment_params(description)

    if not payment_params:
        logger.warning(
            'Invalid pattern for "{}"'.format(description),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_INVALID_PATTERN},
        )
        return

    process_payment_complaint_search.apply_async(
        kwargs=dict(
            payment_data=payment_data,
            payment_params=payment_params,
        )
    )


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_search(self, payment_data, payment_params, cookies=None, *args, **kwargs):
    complaint_pretty_id = payment_params.get("complaint")
    client_request_id = uuid4().hex
    try:
        response = request_cdb_complaint_search(
            complaint_pretty_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception(
            "Request failed: {}, next retry in {} seconds".format(str(exc), countdown),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_SEARCH_EXCEPTION,
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            },
        )
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger.warning(
            "Unexpected status code {} while searching complaint {}".format(response.status_code, complaint_pretty_id),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_SEARCH_CODE_ERROR,
                "STATUS_CODE": response.status_code,
            },
        )
        if response.status_code == 412:
            raise self.retry(
                countdown=0,
                kwargs=dict(
                    payment_data=payment_data,
                    payment_params=payment_params,
                    cookies=cookies,
                ),
            )
        countdown = get_exponential_request_retry_countdown(self, response)
        raise self.retry(countdown=countdown)

    search_complaints_data = response.json()["data"]

    if len(search_complaints_data) == 0:
        logger.warning(
            "Invalid payment complaint {}".format(complaint_pretty_id),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_SEARCH_FAILED},
        )
        if self.request.retries >= COMPLAINT_NOT_FOUND_MAX_RETRIES:
            logger.warning(
                "Invalid payment complaint {}".format(complaint_pretty_id),
                payment_data=payment_data,
                task=self,
                extra={"MESSAGE_ID": PAYMENTS_SEARCH_INVALID_COMPLAINT},
            )
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

    logger.info(
        "Successfully found complaint {}".format(complaint_pretty_id),
        payment_data=payment_data,
        task=self,
        extra={"MESSAGE_ID": PAYMENTS_SEARCH_SUCCESS},
    )

    if not check_complaint_code(search_complaint_data, payment_params):
        logger.info(
            "Invalid payment code {} while searching complaint {}".format(
                payment_params.get("code"), complaint_pretty_id
            ),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_SEARCH_INVALID_CODE},
        )
        return

    logger.info(
        "Successfully matched payment code {} for complaint {}".format(payment_params.get("code"), complaint_pretty_id),
        payment_data=payment_data,
        task=self,
        extra={"MESSAGE_ID": PAYMENTS_SEARCH_VALID_CODE},
    )

    process_payment_complaint_data.apply_async(
        kwargs=dict(complaint_params=complaint_params, payment_data=payment_data, cookies=cookies)
    )


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_data(self, complaint_params, payment_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_cdb_complaint_data(
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception(
            "Request failed: {}, next retry in {} seconds".format(str(exc), countdown),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_EXCEPTION,
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            },
        )
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger_method = get_task_retry_logger_method(self, logger)
        logger_method(
            "Unexpected status code {} while getting complaint {}".format(response.status_code, complaint_id),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_CODE_ERROR,
                "STATUS_CODE": response.status_code,
            },
        )
        if response.status_code == 412:
            raise self.retry(
                countdown=0,
                kwargs=dict(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    cookies=cookies,
                ),
            )
        countdown = get_exponential_request_retry_countdown(self, response)
        raise self.retry(countdown=countdown)
    else:
        logger.info(
            "Successfully retrieved complaint {}".format(complaint_id),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_GET_COMPLAINT_SUCCESS},
        )

    complaint_data = response.json()["data"]

    if not check_complaint_status(complaint_data):
        logger.warning(
            "Invalid complaint status: {}".format(complaint_data["status"]),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_INVALID_STATUS},
        )
        return

    if not check_complaint_value(complaint_data):
        logger.info(
            "Invalid complaint value amount or currency for complaint {}".format(complaint_id),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_INVALID_COMPLAINT_VALUE},
        )
        return

    value = complaint_data.get("value", {})

    if not check_complaint_value_amount(complaint_data, payment_data):
        logger.warning(
            "Invalid payment amount for complaint {}: {} not equal {}".format(
                complaint_id, payment_data.get("amount"), value.get("amount")
            ),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_INVALID_AMOUNT},
        )
        process_payment_complaint_patch.apply_async(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
                cookies=cookies,
            )
        )
        return

    if not check_complaint_value_currency(complaint_data, payment_data):
        logger.warning(
            "Invalid payment amount for complaint {}: {} not equal {}".format(
                complaint_id, payment_data.get("currency"), value.get("currency")
            ),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_INVALID_CURRENCY},
        )
        process_payment_complaint_patch.apply_async(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
                cookies=cookies,
            )
        )
        return

    logger.info(
        "Successfully matched payment for complaint {}".format(complaint_id),
        payment_data=payment_data,
        task=self,
        extra={"MESSAGE_ID": PAYMENTS_VALID_PAYMENT},
    )

    process_payment_complaint_patch.apply_async(
        kwargs=dict(
            payment_data=payment_data,
            complaint_params=complaint_params,
            patch_data={"status": STATUS_COMPLAINT_PENDING},
            cookies=cookies,
        )
    )


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_patch(self, payment_data, complaint_params, patch_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_cdb_complaint_patch(
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
        logger.exception(
            "Request failed: {}, next retry in {} seconds".format(str(exc), countdown),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            },
        )
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    if response.status_code != 200:
        logger_method = get_task_retry_logger_method(self, logger)
        logger_method(
            "Unexpected status code {} while patching complaint {} of tender {}: {}".format(
                response.status_code, complaint_id, tender_id, patch_data
            ),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
                "STATUS_CODE": response.status_code,
            },
        )
        if response.status_code == 412:
            raise self.retry(
                countdown=0,
                kwargs=dict(
                    payment_data=payment_data,
                    complaint_params=complaint_params,
                    patch_data=patch_data,
                    cookies=cookies,
                ),
            )
        elif response.status_code == 403:
            process_payment_complaint_recheck.apply_async(
                kwargs=dict(
                    payment_data=payment_data, complaint_params=complaint_params, patch_data=patch_data, cookies=cookies
                )
            )
            return
        else:
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)
    else:
        complaint_data = response.json()["data"]
        author = complaint_data.get("author")
        if author:
            try:
                set_payment_complaint_author(payment_data, author)
            except PyMongoError:
                pass
        if patch_data.get("status") == STATUS_COMPLAINT_PENDING:
            message_id = PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
        else:
            message_id = PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
        logger.info(
            "Successfully updated complaint {} of tender {}: {}".format(complaint_id, tender_id, patch_data),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": message_id},
        )


@app.task(bind=True, max_retries=1000)
def process_payment_complaint_recheck(self, payment_data, complaint_params, patch_data, cookies=None, *args, **kwargs):
    tender_id = complaint_params.get("tender_id")
    item_type = complaint_params.get("item_type")
    item_id = complaint_params.get("item_id")
    complaint_id = complaint_params.get("complaint_id")
    client_request_id = uuid4().hex
    try:
        response = request_cdb_complaint_data(
            tender_id=tender_id,
            item_type=item_type,
            item_id=item_id,
            complaint_id=complaint_id,
            client_request_id=client_request_id,
            cookies=cookies,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        countdown = get_exponential_request_retry_countdown(self)
        logger.exception(
            "Request failed: {}, next retry in {} seconds".format(str(exc), countdown),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            },
        )
        raise self.retry(countdown=countdown, exc=exc)

    cookies = cookies or {}
    cookies.update(response.cookies.get_dict())

    complaint_id = complaint_params.get("complaint_id")
    tender_id = complaint_params.get("tender_id")

    if response.status_code != 200:
        logger_method = get_task_retry_logger_method(self, logger)
        logger_method(
            "Unexpected status code {} while getting complaint {} of tender {}".format(
                response.status_code, complaint_id, tender_id
            ),
            payment_data=payment_data,
            task=self,
            extra={
                "MESSAGE_ID": PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
                "STATUS_CODE": response.status_code,
            },
        )
        if response.status_code == 412:
            raise self.retry(
                countdown=0,
                kwargs=dict(
                    payment_data=payment_data,
                    complaint_params=complaint_params,
                    patch_data=patch_data,
                    cookies=cookies,
                ),
            )
        else:
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)
    else:
        complaint_get_data = response.json()["data"]
        if complaint_get_data.get("status") == patch_data.get("status"):
            if patch_data.get("status") == STATUS_COMPLAINT_PENDING:
                message_id = PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
            else:
                message_id = PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
            logger.info(
                "Successfully updated complaint {} of tender {}: {}".format(complaint_id, tender_id, patch_data),
                payment_data=payment_data,
                task=self,
                extra={"MESSAGE_ID": message_id},
            )
        else:
            process_payment_complaint_data.apply_async(
                kwargs=dict(payment_data=payment_data, complaint_params=complaint_params, cookies=cookies)
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
        logger.exception(
            str(exc),
            extra={
                "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_EXCEPTION",
                "CDB_CLIENT_REQUEST_ID": client_request_id,
            },
        )
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    else:
        if response.status_code != 200:
            logger_method = get_task_retry_logger_method(self, logger)
            logger_method(
                "Unexpected status code {} while getting tender {}: {}".format(
                    response.status_code, tender_id, response.text
                ),
                extra={
                    "MESSAGE_ID": "PAYMENTS_CRAWLER_GET_TENDER_UNSUCCESSFUL_CODE",
                    "STATUS_CODE": response.status_code,
                },
            )
            countdown = get_exponential_request_retry_countdown(self, response)
            raise self.retry(countdown=countdown)

        tender = response.json()["data"]

        for complaint_data in tender.get("complaints", []):
            if complaint_data["status"] in ALLOWED_COMPLAINT_RESOLUTION_STATUSES:
                complaint_params = {
                    "item_id": None,
                    "item_type": None,
                    "complaint_id": complaint_data["id"],
                    "tender_id": tender_id,
                }
                process_complaint_params.apply_async(
                    kwargs=dict(complaint_params=complaint_params, complaint_data=complaint_data)
                )

        for item_type in ["qualifications", "awards", "cancellations"]:
            for item_data in tender.get(item_type, []):
                for complaint_data in item_data.get("complaints", []):
                    if complaint_data["status"] in ALLOWED_COMPLAINT_RESOLUTION_STATUSES:
                        complaint_params = {
                            "item_id": item_data["id"],
                            "item_type": item_type,
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id,
                        }
                        process_complaint_params.apply_async(
                            kwargs=dict(complaint_params=complaint_params, complaint_data=complaint_data)
                        )


@app.task(bind=True, max_retries=1000)
@formatter.omit(["complaint_data"])
def process_complaint_params(self, complaint_params, complaint_data):
    try:
        payment = get_payment_item_by_params(
            complaint_params, [PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS, PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS]
        )
    except PyMongoError as exc:
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    if payment:
        if not payment.get("resolution"):
            process_complaint_resolution.apply_async(
                kwargs=dict(payment_data=payment.get("payment"), complaint_data=complaint_data)
            )
    else:
        logger.warning(
            "Payment not found for complaint {} with params: {}".format(complaint_data["id"], complaint_params),
            extra={"MESSAGE_ID": "PAYMENTS_CRAWLER_PAYMENT_NOT_FOUND"},
        )


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
        logger.info(
            "Successfully saved complaint {} resolution".format(complaint_data["id"]),
            payment_data=payment_data,
            task=self,
            extra={"MESSAGE_ID": PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS},
        )


@app.task(bind=True, max_retries=10)
def check_services_status(self):
    data = health()
    save_health_data(data)
