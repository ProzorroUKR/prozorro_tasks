from decimal import Decimal, Context, Inexact, InvalidOperation

import dateutil.parser
from pymongo.errors import PyMongoError

from environment_settings import TIMEZONE
from payments.message_ids import (
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_SEARCH_FAILED,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_GET_COMPLAINT_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_CODE_ERROR,
    PAYMENTS_SEARCH_SUCCESS,
    PAYMENTS_SEARCH_VALID_CODE,
    PAYMENTS_GET_TENDER_SUCCESS,
    PAYMENTS_VALID_ITEM,
    PAYMENTS_VALID_PAYMENT,
    PAYMENTS_GET_COMPLAINT_SUCCESS,
    PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
)
from payments.messages import (
    DESC_REJECT_REASON_LAW_NON_COMPLIANCE,
    DESC_REJECT_REASON_ALREADY_EXISTS,
    DESC_REJECT_REASON_BUYER_VIOLATIONS_CORRECTED,
    DESC_REJECT_REASON_TENDER_CANCELLED,
    DESC_REJECT_REASON_CANCELLED_BY_COMPLAINANT,
    DESC_REJECT_REASON_COMPLAINT_PERIOD_ENDED,
    DESC_REJECT_REASON_INCORRECT_PAYMENT,
    DESC_FUNDS_STATE,
    DESC_FUNDS_COMPLAINANT,
    DESC_COMPLAINT_STATUS_DRAFT,
    DESC_COMPLAINT_STATUS_PENDING,
    DESC_COMPLAINT_STATUS_MISTAKEN,
    DESC_COMPLAINT_STATUS_RESOLVED,
    DESC_COMPLAINT_STATUS_INVALID,
    DESC_COMPLAINT_STATUS_SATISFIED,
    DESC_COMPLAINT_STATUS_DECLINED,
    DESC_COMPLAINT_STATUS_ACCEPTED,
    DESC_COMPLAINT_STATUS_STOPPED,
    DESC_PROCESSING_INFO,
    DESC_PROCESSING_SUCCESS,
    DESC_PROCESSING_WARNING,
    DESC_PROCESSING_DANGER,
    DESC_PROCESSING_FAILED,
    DESC_FUNDS_UNKNOWN,
    DESC_PROCESSING_DEFAULT,
    DESC_PROCESSING_NEUTRAL,
    DESC_FUNDS_ALL, DESC_COMPLAINT_STATUS_NOT_PENDING,
)


DEFAULT_CURRENCY = "UAH"


def complaint_status_description(status):
    return COMPLAINT_STATUS_DICT.get(status, status)


def complaint_reject_description(reason):
    return DESC_REJECT_REASON_DICT.get(reason, reason)


def complaint_funds_description(funds):
    return DESC_FUNDS_DICT.get(funds, funds)


def payment_message_status(message):
    if message is None:
        return None
    message_id = message.get("message_id")
    for key, value in PAYMENTS_MESSAGE_IDS.items():
        if message_id in value:
            return key
    return None


def payment_message_list_status(messages):
    return payment_message_status(
        payment_primary_message(messages)
    )


def processing_message_description(processing_status):
    return DESC_PROCESSING_DICT.get(processing_status, processing_status) or DESC_PROCESSING_DEFAULT


def processing_message_list_description(messages):
    return processing_message_description(
        payment_message_list_status(messages)
    )


def processing_message_failed_list_description(messages):
    return processing_message_failed_description(
        payment_primary_message(messages)
    )


def processing_message_failed_description(message):
    if message is None:
        return None
    message_status = payment_message_status(message)
    if message_status == FAILED_MESSAGE_STATUS:
        message_id = message.get("message_id")
        return MESSAGE_ID_DESCRIPTION_DICT.get(message_id, message_id)


def processing_date(data):
    primary_message = payment_primary_message(data.get("messages", []))
    if primary_message and primary_message.get("message_id") in PAYMENTS_FAILED_MESSAGE_ID_LIST:
        return date_representation(primary_message.get("createdAt"))
    resolution = data.get("resolution")
    if resolution:
        return date_representation(resolution.get("date"))


def lazy_set_author(func):
    def wrapper(data):
        if not data.get("author"):
            from payments.cached import get_complaint
            complaint_data = get_complaint(data.get("params"))
            if complaint_data:
                author = complaint_data.get("author")
                if author and complaint_data.get("status") != STATUS_COMPLAINT_DRAFT:
                    from payments.results_db import set_payment_complaint_author
                    try:
                        set_payment_complaint_author(data.get("payment"), author)
                    except PyMongoError as exc:
                        pass
                data["author"] = author
        return func(data)
    return wrapper


@lazy_set_author
def complainant_id(data):
    author = data.get("author", {})
    identifier = author.get("identifier", {})
    scheme = identifier.get("scheme")
    if scheme == "UA-EDR":
        complainant_id = identifier.get("id")
        return complainant_id


@lazy_set_author
def complainant_name(data):
    author = data.get("author", {})
    identifier = author.get("identifier", {})
    name = identifier.get("legalName")
    return name


@lazy_set_author
def complainant_telephone(data):
    author = data.get("author", {})
    contact = author.get("contactPoint", {})
    telephone = contact.get("telephone")
    return telephone


def complainant_status(data):
    status = None
    resolution = data.get("resolution")
    if resolution:
        return DESC_COMPLAINT_STATUS_NOT_PENDING
    from payments.cached import get_complaint
    complaint_data = get_complaint(data.get("params"))
    if complaint_data:
        status = complaint_data.get("status")
    if status:
        return complaint_status_description(status)


def payment_primary_message(messages):
    for priority in MESSAGE_ID_PRIORITY:
        for message in messages or []:
            if message.get("message_id") == priority:
                return message


def date_representation(dt):
    if not dt:
        return None
    if type(dt) is str:
        dt = dateutil.parser.parse(dt)
    return dt.astimezone(TIMEZONE).replace(microsecond=0).isoformat(sep=" ")


def amount_convert(amount):
    amount_decimal = Decimal(str(amount))
    quantize_exp = Decimal(10) ** min(-2, amount_decimal.as_tuple().exponent)
    quantize_context = Context(traps=[InvalidOperation, Inexact])
    try:
        return amount_decimal.quantize(exp=quantize_exp, context=quantize_context)
    except (Inexact, InvalidOperation):
        return Decimal("NaN")


def value_amount_representation(value):
    if value.get("currency") == DEFAULT_CURRENCY:
        return str(amount_convert(value.get("amount")))
    return None


DESC_REJECT_REASON_DICT = {
    "lawNonCompliance": DESC_REJECT_REASON_LAW_NON_COMPLIANCE,
    "alreadyExists": DESC_REJECT_REASON_ALREADY_EXISTS,
    "buyerViolationsCorrected": DESC_REJECT_REASON_BUYER_VIOLATIONS_CORRECTED,
    "tenderCancelled": DESC_REJECT_REASON_TENDER_CANCELLED,
    "cancelledByComplainant": DESC_REJECT_REASON_CANCELLED_BY_COMPLAINANT,
    "complaintPeriodEnded": DESC_REJECT_REASON_COMPLAINT_PERIOD_ENDED,
    "incorrectPayment": DESC_REJECT_REASON_INCORRECT_PAYMENT,
}


FUNDS_ALL = "all"
FUNDS_STATE = "state"
FUNDS_COMPLAINANT = "complainant"
FUNDS_UNKNOWN = "unknown"


DESC_FUNDS_DICT = {
    FUNDS_ALL: DESC_FUNDS_ALL,
    FUNDS_STATE: DESC_FUNDS_STATE,
    FUNDS_COMPLAINANT: DESC_FUNDS_COMPLAINANT,
    FUNDS_UNKNOWN: DESC_FUNDS_UNKNOWN
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

COMPLAINT_STATUS_DICT = {
    STATUS_COMPLAINT_DRAFT: DESC_COMPLAINT_STATUS_DRAFT,
    STATUS_COMPLAINT_PENDING: DESC_COMPLAINT_STATUS_PENDING,
    STATUS_COMPLAINT_MISTAKEN: DESC_COMPLAINT_STATUS_MISTAKEN,
    STATUS_COMPLAINT_RESOLVED: DESC_COMPLAINT_STATUS_RESOLVED,
    STATUS_COMPLAINT_INVALID: DESC_COMPLAINT_STATUS_INVALID,
    STATUS_COMPLAINT_SATISFIED: DESC_COMPLAINT_STATUS_SATISFIED,
    STATUS_COMPLAINT_DECLINED: DESC_COMPLAINT_STATUS_DECLINED,
    STATUS_COMPLAINT_ACCEPTED: DESC_COMPLAINT_STATUS_ACCEPTED,
    STATUS_COMPLAINT_STOPPED: DESC_COMPLAINT_STATUS_STOPPED,
}


PAYMENTS_INFO_MESSAGE_ID_LIST = [
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
]

PAYMENTS_SUCCESS_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
]

PAYMENTS_WARNING_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
]

PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST = \
    PAYMENTS_INFO_MESSAGE_ID_LIST + \
    PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
    PAYMENTS_WARNING_MESSAGE_ID_LIST

PAYMENTS_FAILED_MESSAGE_ID_LIST = [
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
]

PAYMENTS_DANGER_MESSAGE_ID_LIST = [
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_SEARCH_FAILED,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_GET_COMPLAINT_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_CODE_ERROR,
    PAYMENTS_GET_COMPLAINT_RECHECK_EXCEPTION,
    PAYMENTS_GET_COMPLAINT_RECHECK_CODE_ERROR,
]

PAYMENTS_NEUTRAL_MESSAGE_ID_LIST = [
    PAYMENTS_SEARCH_SUCCESS,
    PAYMENTS_SEARCH_VALID_CODE,
    PAYMENTS_GET_TENDER_SUCCESS,
    PAYMENTS_GET_COMPLAINT_SUCCESS,
    PAYMENTS_VALID_ITEM,
    PAYMENTS_VALID_PAYMENT,
]

INFO_MESSAGE_STATUS = "info"
SUCCESS_MESSAGE_STATUS = "success"
WARNING_MESSAGE_STATUS = "warning"
DANGER_MESSAGE_STATUS = "danger"
NEUTRAL_MESSAGE_STATUS = "neutral"
FAILED_MESSAGE_STATUS = "failed"

PAYMENTS_MESSAGE_IDS = {
    INFO_MESSAGE_STATUS: PAYMENTS_INFO_MESSAGE_ID_LIST,
    SUCCESS_MESSAGE_STATUS: PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    WARNING_MESSAGE_STATUS: PAYMENTS_WARNING_MESSAGE_ID_LIST,
    DANGER_MESSAGE_STATUS: PAYMENTS_DANGER_MESSAGE_ID_LIST,
    NEUTRAL_MESSAGE_STATUS: PAYMENTS_NEUTRAL_MESSAGE_ID_LIST,
    FAILED_MESSAGE_STATUS: PAYMENTS_FAILED_MESSAGE_ID_LIST,
}


DESC_PROCESSING_DICT = {
    INFO_MESSAGE_STATUS: DESC_PROCESSING_INFO,
    SUCCESS_MESSAGE_STATUS: DESC_PROCESSING_SUCCESS,
    WARNING_MESSAGE_STATUS: DESC_PROCESSING_WARNING,
    DANGER_MESSAGE_STATUS: DESC_PROCESSING_DANGER,
    NEUTRAL_MESSAGE_STATUS: DESC_PROCESSING_NEUTRAL,
    FAILED_MESSAGE_STATUS: DESC_PROCESSING_FAILED,
}

MESSAGE_ID_PRIORITY = \
    PAYMENTS_INFO_MESSAGE_ID_LIST + \
    PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
    PAYMENTS_WARNING_MESSAGE_ID_LIST + \
    PAYMENTS_FAILED_MESSAGE_ID_LIST + \
    PAYMENTS_DANGER_MESSAGE_ID_LIST

MESSAGE_ID_DESCRIPTION_DICT = {
    PAYMENTS_INVALID_PATTERN: "Відсутня або некоректна інформація про скаргу у описі призначення платежу",
    PAYMENTS_SEARCH_INVALID_COMPLAINT: "Скаргу не знайдено у центральній базі даних",
    PAYMENTS_SEARCH_INVALID_CODE: "Секретний код платежу вказано некоректно",
    PAYMENTS_INVALID_STATUS: "Некоректний стан скарги у центральній базі даних",
    PAYMENTS_INVALID_COMPLAINT_VALUE: "Відсутні дані про сумму до опалити скарги у центральній базі даних",
}
