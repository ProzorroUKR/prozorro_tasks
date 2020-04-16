import dateutil.parser

from environment_settings import TIMEZONE
from payments.message_ids import (
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
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
)
from payments.messages import (
    DESC_REJECT_REASON_LAW_NON_COMPLIANCE, DESC_REJECT_REASON_ALREADY_EXISTS,
    DESC_REJECT_REASON_BUYER_VIOLATIONS_CORRECTED,
    DESC_REJECT_REASON_TENDER_CANCELLED,
    DESC_REJECT_REASON_CANCELLED_BY_COMPLAINANT,
    DESC_REJECT_REASON_COMPLAINT_PERIOD_ENDED,
    DESC_REJECT_REASON_INCORRECT_PAYMENT,
    DESC_FUNDS_STATE,
    DESC_FUNDS_COMPLAINANT,
    COMPLAINT_STATUS_MISTAKEN,
    COMPLAINT_STATUS_RESOLVED,
    COMPLAINT_STATUS_INVALID,
    COMPLAINT_STATUS_SATISFIED,
    COMPLAINT_STATUS_DECLINED,
    COMPLAINT_STATUS_ACCEPTED,
    COMPLAINT_STATUS_STOPPED,
    DESC_PROCESSING_INFO,
    DESC_PROCESSING_SUCCESS,
    DESC_PROCESSING_WARNING,
    DESC_PROCESSING_DANGER,
    DESC_PROCESSING_FAILED,
    DESC_FUNDS_UNKNOWN,
)


def complaint_status_description(status):
    return COMPLAINT_STATUS_DICT.get(status, status)


def complaint_reject_description(reason):
    return DESC_REJECT_REASON_DICT.get(reason, reason)


def complaint_funds_description(funds):
    return DESC_FUNDS_DICT.get(funds, funds)


def processing_message_description(processing_status):
    return DESC_PROCESSING_DICT.get(processing_status, processing_status)


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


def processing_message_list_description(messages):
    return processing_message_description(
        payment_message_list_status(messages)
    )


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
    return dt.astimezone(TIMEZONE).replace(microsecond=0).isoformat()


DESC_REJECT_REASON_DICT = {
    "lawNonCompliance": DESC_REJECT_REASON_LAW_NON_COMPLIANCE,
    "alreadyExists": DESC_REJECT_REASON_ALREADY_EXISTS,
    "buyerViolationsCorrected": DESC_REJECT_REASON_BUYER_VIOLATIONS_CORRECTED,
    "tenderCancelled": DESC_REJECT_REASON_TENDER_CANCELLED,
    "cancelledByComplainant": DESC_REJECT_REASON_CANCELLED_BY_COMPLAINANT,
    "complaintPeriodEnded": DESC_REJECT_REASON_COMPLAINT_PERIOD_ENDED,
    "incorrectPayment": DESC_REJECT_REASON_INCORRECT_PAYMENT,
}


DESC_FUNDS_DICT = {
    "state": DESC_FUNDS_STATE,
    "complainant": DESC_FUNDS_COMPLAINANT,
    "unknown": DESC_FUNDS_UNKNOWN
}


COMPLAINT_STATUS_DICT = dict(
    mistaken=COMPLAINT_STATUS_MISTAKEN,
    resolved=COMPLAINT_STATUS_RESOLVED,
    invalid=COMPLAINT_STATUS_INVALID,
    satisfied=COMPLAINT_STATUS_SATISFIED,
    declined=COMPLAINT_STATUS_DECLINED,
    accepted=COMPLAINT_STATUS_ACCEPTED,
    stopped=COMPLAINT_STATUS_STOPPED,
)


PAYMENTS_INFO_MESSAGE_ID_LIST = [
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
]

PAYMENTS_SUCCESS_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
]

PAYMENTS_WARNING_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
]

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
]

PAYMENTS_MESSAGE_IDS = {
    "info": PAYMENTS_INFO_MESSAGE_ID_LIST,
    "success": PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    "warning": PAYMENTS_WARNING_MESSAGE_ID_LIST,
    "danger": PAYMENTS_DANGER_MESSAGE_ID_LIST,
    "failed": PAYMENTS_FAILED_MESSAGE_ID_LIST,
}


DESC_PROCESSING_DICT = {
    "info": DESC_PROCESSING_INFO,
    "success": DESC_PROCESSING_SUCCESS,
    "warning": DESC_PROCESSING_WARNING,
    "danger": DESC_PROCESSING_DANGER,
    "failed": DESC_PROCESSING_FAILED,
}

MESSAGE_ID_PRIORITY = \
    PAYMENTS_INFO_MESSAGE_ID_LIST + \
    PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
    PAYMENTS_WARNING_MESSAGE_ID_LIST + \
    PAYMENTS_FAILED_MESSAGE_ID_LIST + \
    PAYMENTS_DANGER_MESSAGE_ID_LIST
