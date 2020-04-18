import re
from hashlib import sha512
from uuid import uuid4

import requests
from celery.utils.log import get_task_logger

from environment_settings import API_HOST, API_VERSION, API_TOKEN
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT

logger = get_task_logger(__name__)

PAYMENT_RE = re.compile(
    r"(?P<complaint>UA-\d{4}-\d{2}-\d{2}-\d{6}(?:-\w)?(?:\.\d+)?\.(?:\w)?\d+)-(?P<code>[0-9a-f]*)",
    re.IGNORECASE
)

ALLOWED_COMPLAINT_PAYMENT_STATUSES = ["draft"]


def get_payment_params(description):
    match = PAYMENT_RE.search(description)
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


def get_complaint_search_url(complaint_pretty_id, host=None):
    url_pattern = "{host}/api/{version}/complaints/search?complaint_id={complaint_pretty_id}"
    return url_pattern.format(
        host=host or API_HOST,
        version=API_VERSION,
        complaint_pretty_id=complaint_pretty_id
    )


def get_complaint_url(tender_id, item_type, item_id, complaint_id, host=None):
    if item_type:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"
    return url_pattern.format(
        host=host or API_HOST,
        version=API_VERSION,
        tender_id=tender_id,
        item_type=item_type,
        item_id=item_id,
        complaint_id=complaint_id,
    )


def get_tender_url(tender_id, host=None):
    url_pattern = "{host}/api/{version}/tenders/{tender_id}"
    return url_pattern.format(
        host=host or API_HOST,
        version=API_VERSION,
        tender_id=tender_id
    )


def request_complaint_search(complaint_pretty_id, client_request_id=None, cookies=None, host=None):
    url = get_complaint_search_url(complaint_pretty_id, host=host)
    client_request_id = client_request_id or uuid4().hex
    headers = {
        "X-Client-Request-ID": client_request_id,
        "Authorization": "Bearer {}".format(API_TOKEN),
    }
    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.get(url, headers=headers, timeout=timeout, cookies=cookies)


def request_tender_data(tender_id, client_request_id=None, cookies=None, host=None):
    url = get_tender_url(tender_id, host=host)
    client_request_id = client_request_id or uuid4().hex
    headers = {"X-Client-Request-ID": client_request_id}
    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.get(url, headers=headers, timeout=timeout, cookies=cookies)


def request_complaint_data(tender_id, item_type, item_id, complaint_id,
                           client_request_id=None, cookies=None, host=None):
    url = get_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    client_request_id = client_request_id or uuid4().hex
    headers = {"X-Client-Request-ID": client_request_id}
    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.get(url, headers=headers, timeout=timeout, cookies=cookies)


def request_complaint_patch(tender_id, item_type, item_id, complaint_id, data,
                            client_request_id=None, cookies=None, host=None):
    url = get_complaint_url(tender_id, item_type, item_id, complaint_id, host=host)
    headers = {
        "X-Client-Request-ID": client_request_id,
        "Authorization": "Bearer {}".format(API_TOKEN),
    }
    timeout = (CONNECT_TIMEOUT, READ_TIMEOUT)
    return requests.patch(url, json={"data": data}, headers=headers, timeout=timeout, cookies=cookies)
