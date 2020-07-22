import re
import requests

from hashlib import sha512
from uuid import uuid4

from celery.utils.log import get_task_logger

from environment_settings import API_HOST, API_VERSION, API_TOKEN, PUBLIC_API_HOST
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT

logger = get_task_logger(__name__)

PAYMENT_RE = re.compile(
    r"(?P<complaint>UA-\d{4}-\d{2}-\d{2}-\d{6}(?:-\w)?(?:\.\d+)?\.(?:\w)?\d+)-(?P<code>.{8})",
    re.IGNORECASE
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
    # replace punctuation marks
    "[^\w]*[\,]+[^\w]*": ".",
    "[^\w\.\,]+": "-",
}

STATUS_COMPLAINT_DRAFT = "draft"
STATUS_COMPLAINT_PENDING = "pending"
STATUS_COMPLAINT_ACCEPTED = "accepted"
STATUS_COMPLAINT_MISTAKEN = "mistaken"
STATUS_COMPLAINT_SATISFIED = "satisfied"
STATUS_COMPLAINT_RESOLVED = "resolved"
STATUS_COMPLAINT_INVALID = "invalid"
STATUS_COMPLAINT_STOPPED = "stopped"
STATUS_COMPLAINT_DECLINED = "declined"

ALLOWED_COMPLAINT_PAYMENT_STATUSES = [STATUS_COMPLAINT_DRAFT]
ALLOWED_COMPLAINT_RESOLUTION_STATUSES = [
    STATUS_COMPLAINT_MISTAKEN,
    STATUS_COMPLAINT_SATISFIED,
    STATUS_COMPLAINT_RESOLVED,
    STATUS_COMPLAINT_INVALID,
    STATUS_COMPLAINT_STOPPED,
    STATUS_COMPLAINT_DECLINED
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


def find_replace(string, dictionary):
    for item in dictionary.keys():
        string = re.sub(item, dictionary[item], string)
    return string


def get_payment_params(description):
    match = PAYMENT_RE.search(find_replace(description, PAYMENT_REPLACE_MAPPING))
    if match:
        return match.groupdict()


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
    return url_pattern.format(
        host=API_HOST,
        version=API_VERSION,
        complaint_pretty_id=complaint_pretty_id
    )


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
    return url_pattern.format(
        host=host,
        version=API_VERSION,
        tender_id=tender_id
    )


def get_cdb_spore_url(host=PUBLIC_API_HOST):
    url_pattern = "{host}/api/{version}/spore"
    return url_pattern.format(
        host=host,
        version=API_VERSION,
    )


def get_cdb_request_headers(client_request_id=None, authorization=False):
    client_request_id = client_request_id or "req-payments-" + str(uuid4())
    headers = {"X-Client-Request-ID": client_request_id}
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
    return request_cdb_head(
        url=url,
        client_request_id=client_request_id,
        cookies=cookies,
        timeout=timeout
    )


def request_cdb_complaint_search(complaint_pretty_id, client_request_id=None,
                                 cookies=None, timeout=None):
    url = get_cdb_complaint_search_url(complaint_pretty_id)
    return request_cdb_get(
        url=url,
        client_request_id=client_request_id,
        cookies=cookies,
        timeout=timeout,
        authorization=True
    )


def request_cdb_tender_data(tender_id, client_request_id=None,
                            cookies=None, timeout=None, host=PUBLIC_API_HOST):
    url = get_cdb_tender_url(tender_id, host=host)
    return request_cdb_get(
        url=url,
        client_request_id=client_request_id,
        cookies=cookies,
        timeout=timeout
    )


def request_cdb_complaint_data(tender_id, item_type, item_id, complaint_id, client_request_id=None,
                               cookies=None, timeout=None, host=API_HOST):
    url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    return request_cdb_get(
        url=url,
        client_request_id=client_request_id,
        cookies=cookies,
        timeout=timeout
    )


def request_cdb_complaint_patch(tender_id, item_type, item_id, complaint_id, data, client_request_id=None,
                                cookies=None, timeout=None, host=API_HOST):
    url = get_cdb_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    return request_cdb_patch(
        url=url,
        data=data,
        client_request_id=client_request_id,
        cookies=cookies,
        timeout=timeout
    )


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
