import re
from hashlib import sha512

from celery.utils.log import get_task_logger


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
