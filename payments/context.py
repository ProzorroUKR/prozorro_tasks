import dateutil.parser
import requests
from flask import request, url_for
from flask_paginate import Pagination

from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.schemes import payment_scheme, resolution_scheme, full_scheme, get_scheme_value, get_scheme_data
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
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
)
from payments.results_db import get_payment_count

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10

CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 3.0

PAYMENTS_INFO_MESSAGE_ID_LIST = [
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
]

PAYMENTS_SUCCESS_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
]

PAYMENTS_WARNING_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
]

PAYMENTS_DANGER_MESSAGE_ID_LIST = [
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
]

PAYMENTS_ERROR_MESSAGE_ID_LIST = [
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
]

PAYMENTS_MESSAGE_IDS = {
    'success': PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    'warning': PAYMENTS_WARNING_MESSAGE_ID_LIST,
    'danger': PAYMENTS_DANGER_MESSAGE_ID_LIST,
    'error': PAYMENTS_ERROR_MESSAGE_ID_LIST,
}


def get_tender(params):
    url_pattern = "{host}/api/{version}/tenders/{tender_id}"
    url = url_pattern.format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        **params
    )
    try:
        response = requests.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except Exception as exc:
        pass
    else:
        tender = response.json()["data"]
        return tender


def get_complaint(params):
    if params.get("item_type"):
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "{host}/api/{version}/tenders/{tender_id}/complaints/{complaint_id}"
    url = url_pattern.format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        **params
    )
    try:
        response = requests.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except Exception as exc:
        pass
    else:
        complaint = response.json()["data"]
        return complaint


def url_for_search(endpoint, exclude=None, include=None):
    args = request.args
    exclude = exclude or []
    args = {key: value for key, value in args.items() if value and key not in exclude}
    if include:
        args.update(**include)
    args = {key: value for key, value in args.items() if value}
    return url_for(endpoint, **args)


def get_payment_search_params():
    try:
        page = int(request.args.get("page", DEFAULT_PAGE))
    except ValueError:
        page = DEFAULT_PAGE
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT
    payment_type = request.args.get("type", None)
    query = request.args.get("query", None)
    return dict(
        limit=limit,
        page=page,
        payment_type=payment_type,
        search=query
    )


def get_report_params():
    date_str = request.args.get("date")
    if date_str:
        try:
            date = dateutil.parser.parse(date_str)
        except Exception:
            date = None
    else:
        date = None
    funds = request.args.get("funds", None)
    return dict(
        resolution_date=date,
        resolution_funds=funds,
    )

def get_payment_pagination(**kwargs):
    return Pagination(
        bs_version=4,
        link_size="sm",
        show_single_page=True,
        record_name="payments",
        total=get_payment_count(**kwargs),
        per_page_parameter="limit",
        page_parameter="page",
        **kwargs
    )

def get_payments(rows):
    return [get_payment(row) for row in rows]

def get_payment(row):
    data = get_scheme_data(row, full_scheme)
    data["messages"] = row.get("messages", [])
    data["params"] = row.get("params", {})
    return data


def get_report(rows):
    data = []
    headers = []

    for key, value in payment_scheme.items():
        headers.append(value["title"])
    for key, value in resolution_scheme.items():
        headers.append(value["title"])

    for row in rows:
        item = []
        for key, scheme in payment_scheme.items():
            value = get_scheme_value(row, scheme)
            item.append(value)
        for key, scheme in resolution_scheme.items():
            value = get_scheme_value(row, scheme)
            item.append(value)
        data.append(item)

    data.insert(0, headers)

    return data


def payment_primary_message(payment):
    primary_list = []
    primary_list.extend(PAYMENTS_INFO_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_SUCCESS_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_WARNING_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_DANGER_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_ERROR_MESSAGE_ID_LIST)
    for primary in primary_list:
        for message in payment.get("messages", []):
            if message.get("message_id") == primary:
                return message


def payment_message_status(message):
    if message is None:
        return None
    message_id = message.get("message_id")
    if message_id in PAYMENTS_INFO_MESSAGE_ID_LIST:
        return "info"
    if message_id in PAYMENTS_SUCCESS_MESSAGE_ID_LIST:
        return "success"
    elif message_id in PAYMENTS_WARNING_MESSAGE_ID_LIST:
        return "warning"
    elif message_id in PAYMENTS_ERROR_MESSAGE_ID_LIST:
        return "warning"
    elif message_id in PAYMENTS_DANGER_MESSAGE_ID_LIST:
        return "danger"
    return None
