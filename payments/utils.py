from celery.utils.log import get_task_logger

from payments.settings import (
    ALLOWED_COMPLAINT_PAYMENT_STATUSES,
    COMPLAINT_RE_DICT,
)

logger = get_task_logger(__name__)


def get_complaint_type(description):
    for complaint_type, complaint_re in COMPLAINT_RE_DICT.items():
        if complaint_re.search(description):
            return complaint_type


def get_complaint_params(description, complaint_type):
    match = COMPLAINT_RE_DICT[complaint_type].search(description)
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
