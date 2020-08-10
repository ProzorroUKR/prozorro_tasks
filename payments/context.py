from datetime import datetime

from flask import request, url_for
from flask_paginate import Pagination

from payments.messages import DESC_REPORT_TOTAL
from payments.schemes import (
    get_scheme_value,
    get_scheme_data,
    ROOT_SCHEME,
    REPORT_SCHEME,
)

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10


def url_for_search(endpoint, exclude=None, include=None):
    args = request.args
    exclude = exclude or []
    args = {key: value for key, value in args.items() if value and key not in exclude}
    if include:
        args.update(**include)
    args = {key: value for key, value in args.items() if value}
    return url_for(endpoint, **args)


def get_string_param(name, default=None):
    return request.args.get(name, default)


def get_int_param(name, default=None):
    try:
        param = int(request.args.get(name, default))
    except ValueError:
        param = default
    return param


def get_date_param(name, date_format, default=None):
    date_str = request.args.get(name)
    if date_str:
        try:
            date = datetime.strptime(date_str, date_format)
        except ValueError:
            date = default
    else:
        date = default
    return date


def get_payment_search_params():
    page = get_int_param("page", DEFAULT_PAGE)
    limit = get_int_param("limit", DEFAULT_LIMIT)
    payment_type = get_string_param("type")
    payment_source = get_string_param("source")
    query = get_string_param("query")
    payment_date_from = get_date_param("date_oper_from", "%Y-%m-%d")
    payment_date_to = get_date_param("date_oper_to", "%Y-%m-%d")
    return dict(
        limit=limit,
        page=page,
        search=query,
        payment_type=payment_type,
        payment_source=payment_source,
        payment_date_from=payment_date_from,
        payment_date_to=payment_date_to,
    )


def get_report_params():
    funds = get_string_param("funds")
    date_from = get_date_param("date_resolution_from", "%Y-%m-%d")
    date_to = get_date_param("date_resolution_to", "%Y-%m-%d")
    return dict(
        funds=funds,
        date_resolution_from=date_from,
        date_resolution_to=date_to,
    )


def get_request_params():
    date_from = get_date_param("date_from", "%Y-%m-%d")
    date_to = get_date_param("date_to", "%Y-%m-%d")
    return dict(
        date_from=date_from,
        date_to=date_to,
    )

def get_payment_pagination(total=None, **kwargs):
    return Pagination(
        bs_version=4,
        link_size="sm",
        show_single_page=True,
        record_name="payments",
        total=total,
        per_page_parameter="limit",
        page_parameter="page",
        **kwargs
    )

def get_payments(rows):
    return [get_payment(row) for row in rows]

def get_payment(row):
    return get_scheme_data(row, ROOT_SCHEME)

def get_report(rows, total=False):
    data = []
    headers = []

    amount_total = 0

    for key, value in REPORT_SCHEME.items():
        headers.append(value["title"])

    for row in rows:
        item = []
        if total:
            payment = row.get("payment", {})
            amount_total += float(payment.get("amount", 0.0))
        for key, scheme in REPORT_SCHEME.items():
            value = get_scheme_value(row, scheme) or ""
            item.append(value)
        data.append(item)

    data.insert(0, headers)

    if total:
        data.append([DESC_REPORT_TOTAL, '%g' % (amount_total)])

    return data
