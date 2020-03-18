import re

from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)

COMPLAINT_RE = re.compile(
    r"/\s*tenders\s*/\s*(?P<tender_id>[0-9a-f]{32})\s*"
    r"(?:/\s*(?P<item_type>qualifications|awards|cancellations)\s*/\s*(?P<item_id>[0-9a-f]{32})\s*)?"
    r"/\s*complaints\s*/\s*(?P<complaint_id>[0-9a-f]{32})\s*",
)

ALLOWED_COMPLAINT_PAYMENT_STATUSES = ["draft"]


def get_complaint_params(description):
    match = COMPLAINT_RE.search(description)
    if match:
        return match.groupdict()


def get_item_data(data, items_name, item_id):
    for complaint_data in data.get(items_name, []):
        if complaint_data.get("id") == item_id:
            return complaint_data


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
