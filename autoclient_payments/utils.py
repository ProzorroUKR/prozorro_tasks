import json
import re
import shelve
from datetime import datetime
from json import JSONDecodeError
from typing import Generator, Tuple
from urllib.parse import urlencode

import requests

from hashlib import sha512
from uuid import uuid4

from xlsxwriter import Workbook

from environment_settings import (
    API_HOST,
    API_VERSION,
    API_TOKEN,
    PUBLIC_API_HOST,
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    PB_AUTOCLIENT_NAME,
    PB_AUTOCLIENT_TOKEN,
    PB_ACCOUNT,
)
from autoclient_payments.data import (
    complaint_funds_description,
    STATUS_COMPLAINT_DRAFT,
    STATUS_COMPLAINT_MISTAKEN,
    STATUS_COMPLAINT_SATISFIED,
    STATUS_COMPLAINT_RESOLVED,
    STATUS_COMPLAINT_INVALID,
    STATUS_COMPLAINT_STOPPED,
    STATUS_COMPLAINT_DECLINED,
)
from tasks_utils.settings import DEFAULT_HEADERS

PB_DATA_DT_FORMAT = "%d.%m.%Y %H:%M:%S"
PB_QUERY_DATE_FORMAT = "%d-%m-%Y"

PAYMENT_RE = re.compile(
    r"(?P<complaint>UA-\d{4}-\d{2}-\d{2}-\d{6}(?:-\w)?(?:\.\d+)?\.(?:\w)?\d+)-(?P<code>.{8})", re.IGNORECASE
)

PAYMENT_REPLACE_MAPPING = {
    # delete whitespaces
    "\s+": "",
    # replace cyrillic with latin
    "а": "a",
    "А": "A",
    "В": "B",
    "с": "c",
    "С": "C",
    "е": "e",
    "Е": "E",
    # replace letters with numbers
    "l": "1",
    "I": "1",
    "І": "1",
    "i": "1",
    "і": "1",
    "O": "0",
    "О": "0",
    "з": "3",
    "З": "3",
    "б": "6",
    "Б": "6",
    # replace punctuation marks
    "[^\w]*[\,]+[^\w]*": ".",
    "[^\w\.\,]+": "-",
}

ALLOWED_COMPLAINT_PAYMENT_STATUSES = [STATUS_COMPLAINT_DRAFT]
ALLOWED_COMPLAINT_RESOLUTION_STATUSES = [
    STATUS_COMPLAINT_MISTAKEN,
    STATUS_COMPLAINT_SATISFIED,
    STATUS_COMPLAINT_RESOLVED,
    STATUS_COMPLAINT_INVALID,
    STATUS_COMPLAINT_STOPPED,
    STATUS_COMPLAINT_DECLINED,
]

RESOLUTION_MAPPING = {
    STATUS_COMPLAINT_MISTAKEN: dict(
        type="mistaken",
        funds_by_default=None,
        funds_by_reject_reason={
            "incorrectPayment": "complainant",
            "complaintPeriodEnded": "complainant",
            "cancelledByComplainant": "complainant",
        },
        date_field="date",
    ),
    STATUS_COMPLAINT_SATISFIED: dict(
        type="satisfied",
        funds_by_default="complainant",
        date_field="dateDecision",
    ),
    STATUS_COMPLAINT_RESOLVED: dict(
        type="satisfied",
        funds_by_default="complainant",
        date_field="dateDecision",
    ),
    STATUS_COMPLAINT_INVALID: dict(
        type="invalid",
        funds_by_default="state",
        funds_by_reject_reason={
            "buyerViolationsCorrected": "complainant",
        },
        date_field="dateDecision",
    ),
    STATUS_COMPLAINT_STOPPED: dict(
        type="stopped",
        funds_by_default="state",
        funds_by_reject_reason={
            "buyerViolationsCorrected": "complainant",
        },
        date_field="dateDecision",
    ),
    STATUS_COMPLAINT_DECLINED: dict(
        type="declined",
        funds_by_default="state",
        date_field="dateDecision",
    ),
}

PAYMENT_EXCLUDE_FIELDS = [
    "status",
    "uid",
]


REPORT_COLUMN_SMALL_INDICES = (0,)
REPORT_COLUMN_LARGE_INDICES = (1, 2)

REPORT_COLUMN_DEFAULT_MIN_LEN = 7
REPORT_COLUMN_DEFAULT_MAX_LEN = 15

REPORT_COLUMN_SMALL_MIN_LEN = 3
REPORT_COLUMN_SMALL_MAX_LEN = 10

REPORT_COLUMN_LARGE_MIN_LEN = 7
REPORT_COLUMN_LARGE_MAX_LEN = 25

REPORT_COLUMN_EXTRA_LEN = 1

PB_HEADERS = {
    "User-Agent": PB_AUTOCLIENT_NAME,
    "token": PB_AUTOCLIENT_TOKEN,
    "Content-Type": "application/json;charset=cp1251",
}
PB_TRANSACTIONS_URL = "https://acp.privatbank.ua/api/statements/transactions"


def find_replace(string, dictionary):
    for item in dictionary.keys():
        string = re.sub(item, dictionary[item], string)
    return string


def get_payment_params(description):
    match = PAYMENT_RE.search(find_replace(description, PAYMENT_REPLACE_MAPPING))
    if match:
        params = match.groupdict()
        params["complaint"] = params["complaint"][:2].upper() + params["complaint"][2:].lower()
        params["code"] = params["code"].upper()
        return params


def get_item_data(data, items_name, item_id):
    if data:
        for complaint_data in data.get(items_name, []):
            if complaint_data.get("id") == item_id:
                return complaint_data


def check_complaint_code(complaint_data, payment_params):
    token = complaint_data.get("access", {}).get("token")
    code = payment_params.get("code")
    if token and code:
        return sha512(token.encode()).hexdigest()[:8].lower() == code[:8].lower()
    return False


def check_complaint_status(complaint_data):
    return complaint_data.get("status") in ALLOWED_COMPLAINT_PAYMENT_STATUSES


def check_complaint_value(complaint_data):
    value = complaint_data.get("value", {})
    return value and "amount" in value and "currency" in value


def check_complaint_value_amount(complaint_data, payment_data):
    complaint_value_data = complaint_data.get("value", {})
    if "amount" in payment_data and "amount" in complaint_value_data:
        return float(payment_data["amount"]) == float(complaint_value_data["amount"])
    return False


def check_complaint_value_currency(complaint_data, payment_data):
    complaint_value_data = complaint_data.get("value", {})
    if "currency" in payment_data and "currency" in complaint_value_data:
        return payment_data["currency"] == complaint_data.get("value", {}).get("currency")
    return False


def get_cdb_complaint_search_url(complaint_pretty_id):
    url_pattern = "{host}/api/{version}/complaints/search?complaint_id={complaint_pretty_id}"
    return url_pattern.format(host=API_HOST, version=API_VERSION, complaint_pretty_id=complaint_pretty_id)


def get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id, host=API_HOST):
    if item_type:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"
    return url_pattern.format(
        host=host,
        version=API_VERSION,
        tender_id=tender_id,
        item_type=item_type,
        item_id=item_id,
        complaint_id=complaint_id,
    )


def get_cdb_tender_url(tender_id, host=PUBLIC_API_HOST):
    url_pattern = "{host}/api/{version}/tenders/{tender_id}"
    return url_pattern.format(host=host, version=API_VERSION, tender_id=tender_id)


def get_cdb_spore_url(host=PUBLIC_API_HOST):
    url_pattern = "{host}/api/{version}/spore"
    return url_pattern.format(
        host=host,
        version=API_VERSION,
    )


def get_cdb_request_headers(client_request_id=None, authorization=False):
    client_request_id = client_request_id or "req-payments-" + str(uuid4())
    headers = {
        "X-Client-Request-ID": client_request_id,
        **DEFAULT_HEADERS,
    }
    if authorization:
        headers.update({"Authorization": "Bearer {}".format(API_TOKEN)})
    return headers


def request_cdb_head(url, client_request_id=None, cookies=None, timeout=None):
    headers = get_cdb_request_headers(client_request_id=client_request_id)
    timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.head(url, headers=headers, timeout=timeout, cookies=cookies)


def request_cdb_get(url, client_request_id=None, cookies=None, timeout=None, authorization=False):
    headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=authorization)
    timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.get(url, headers=headers, timeout=timeout, cookies=cookies)


def request_cdb_patch(url, data, client_request_id=None, cookies=None, timeout=None, authorization=True):
    headers = get_cdb_request_headers(client_request_id=client_request_id, authorization=authorization)
    timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.patch(url, json={"data": data}, headers=headers, timeout=timeout, cookies=cookies)


def request_cdb_head_spore(client_request_id=None, cookies=None, timeout=None, host=PUBLIC_API_HOST):
    url = get_cdb_spore_url(host=host)
    return request_cdb_head(url=url, client_request_id=client_request_id, cookies=cookies, timeout=timeout)


def request_cdb_complaint_search(complaint_pretty_id, client_request_id=None, cookies=None, timeout=None):
    url = get_cdb_complaint_search_url(complaint_pretty_id)
    return request_cdb_get(
        url=url, client_request_id=client_request_id, cookies=cookies, timeout=timeout, authorization=True
    )


def request_cdb_tender_data(tender_id, client_request_id=None, cookies=None, timeout=None, host=PUBLIC_API_HOST):
    url = get_cdb_tender_url(tender_id, host=host)
    return request_cdb_get(url=url, client_request_id=client_request_id, cookies=cookies, timeout=timeout)


def request_cdb_complaint_data(
    tender_id, item_type, item_id, complaint_id, client_request_id=None, cookies=None, timeout=None, host=API_HOST
):
    url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    return request_cdb_get(url=url, client_request_id=client_request_id, cookies=cookies, timeout=timeout)


def request_cdb_complaint_patch(
    tender_id, item_type, item_id, complaint_id, data, client_request_id=None, cookies=None, timeout=None, host=API_HOST
):
    url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    return request_cdb_patch(url=url, data=data, client_request_id=client_request_id, cookies=cookies, timeout=timeout)


def request_cdb_cookies():
    client_request_id = uuid4().hex
    head_response = request_cdb_head_spore(client_request_id=client_request_id, host=API_HOST)
    return head_response.cookies.get_dict()


def get_resolution(complaint_data):
    status = complaint_data.get("status")
    resolution_scheme = RESOLUTION_MAPPING.get(status)
    if resolution_scheme:
        resolution_type = resolution_scheme.get("type")
        date_field = resolution_scheme.get("date_field")
        date = complaint_data.get(date_field)
        reject_reason = complaint_data.get("rejectReason")
        funds_by_reject_reason = resolution_scheme.get("funds_by_reject_reason")
        if funds_by_reject_reason and reject_reason in funds_by_reject_reason.keys():
            funds = funds_by_reject_reason.get(reject_reason)
        else:
            funds = resolution_scheme.get("funds_by_default")

        return {
            "type": resolution_type,
            "date": date,
            "reason": reject_reason,
            "funds": funds,
        }


def generate_report_file(filename, data, title):
    total = data.pop(len(data) - 1)
    for index, row in enumerate(data):
        data[index] = [str(index) if index else " "] + row
    headers = data.pop(0)
    workbook = Workbook(filename)
    worksheet = workbook.add_worksheet()
    title_properties = {"text_wrap": True}
    title_cell_format = workbook.add_format(title_properties)
    title_cell_format.set_align("center")
    worksheet.merge_range(0, 0, 0, len(headers) - 1, title, title_cell_format)
    worksheet.add_table(
        1,
        0,
        len(data) + 1,
        len(headers) - 1,
        {"first_column": True, "header_row": True, "columns": [{"header": header} for header in headers], "data": data},
    )
    table_properties = {"text_wrap": True}
    table_cell_format = workbook.add_format(table_properties)
    table_cell_format.set_align("top")
    for index, header in enumerate(headers):
        if index in REPORT_COLUMN_SMALL_INDICES:
            min_default_len = REPORT_COLUMN_SMALL_MIN_LEN
            max_default_len = REPORT_COLUMN_SMALL_MAX_LEN
        elif index in REPORT_COLUMN_LARGE_INDICES:
            min_default_len = REPORT_COLUMN_LARGE_MIN_LEN
            max_default_len = REPORT_COLUMN_LARGE_MAX_LEN
        else:
            min_default_len = REPORT_COLUMN_DEFAULT_MIN_LEN
            max_default_len = REPORT_COLUMN_DEFAULT_MAX_LEN
        max_len = max(max(map(lambda x: len(x[index]), data)) + REPORT_COLUMN_EXTRA_LEN if data else 0, min_default_len)
        width = min(max_len, max_default_len)
        worksheet.set_column(index, index, width, table_cell_format)
    worksheet.write_row(len(data) + 2, 1, total)
    workbook.close()


def generate_report_filename(date_from, date_to, funds):
    if date_from == date_to:
        return "{}-{}-report".format(date_from.date().isoformat(), funds)
    return "{}-{}-{}-report".format(date_from.date().isoformat(), date_to.date().isoformat(), funds)


def generate_report_title(date_from, date_to, funds):
    funds_description = complaint_funds_description(funds)
    if date_from == date_to:
        return "{}: {}".format(funds_description, date_from.date().isoformat())
    return "{}: {} - {}".format(
        funds_description,
        date_from.date().isoformat(),
        date_to.date().isoformat(),
    )


def filter_payment_data(data):
    return {key: value for key, value in data.items() if key not in PAYMENT_EXCLUDE_FIELDS}


def _get_transactions(
    url: str,
    query_args: dict,
) -> Tuple[list, bool, str]:
    resp = requests.get(f"{url}?{urlencode(query_args)}", headers=PB_HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return data.get("transactions", []), data["exist_next_page"], data.get("next_page_id")


def transactions_list(
    start_date: str,
    end_date: str = None,
    limit: int = 100,
    pb_account: str = PB_ACCOUNT,
    url: str = PB_TRANSACTIONS_URL,
) -> Generator[dict, None, None]:
    query_args = {
        "acc": pb_account,
        "limit": limit,
        "startDate": start_date,
    }
    if end_date:
        query_args.update({"endDate": end_date})
    while page_resp := _get_transactions(url, query_args):
        transactions, next_page_exists, next_page_id = page_resp
        for transaction in transactions:
            yield transaction
        if not next_page_exists:
            break
        query_args.update({"followId": next_page_id})


def request_pb_autoclient_head(timeout=None, url="https://acp.privatbank.ua/api/statements/settings"):
    timeout = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.head(url, timeout=timeout, headers=PB_HEADERS)


# --- fake data registry


def get_payments_registry_fake(date_from, date_to):
    if transactions := get_payments_registry_fake_data():

        def fake_date_oper_range(value):
            try:
                date_oper = datetime.strptime(value["DATE_TIME_DAT_OD_TIM_P"], PB_DATA_DT_FORMAT)
            except (ValueError, KeyError, TypeError):
                return False
            return date_from <= date_oper < date_to

        return list(filter(fake_date_oper_range, transactions))


def dumps_payments_registry_fake():
    transactions = get_payments_registry_fake_data()
    if transactions is not None:
        return json.dumps(transactions, indent=4, ensure_ascii=False)


def store_payments_registry_fake(text):
    if not text:
        put_payments_registry_fake_data(None)
    else:
        try:
            data = json.loads(text)
        except JSONDecodeError:
            pass
        else:
            put_payments_registry_fake_data(data)


def put_payments_registry_fake_data(data):
    try:
        with shelve.open("autoclient_payments.db") as db:
            db["registry"] = data
    except OSError:
        pass


def get_payments_registry_fake_data(default=None):
    try:
        with shelve.open("autoclient_payments.db") as db:
            return db.get("registry", default)
    except OSError:
        pass
