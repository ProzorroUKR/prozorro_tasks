from datetime import datetime

import requests
from flask import request, url_for
from flask_paginate import Pagination

from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.schemes import (
    get_scheme_value,
    get_scheme_data,
    ROOT_SCHEME,
    REPORT_SCHEME,
)
from payments.results_db import get_payment_count, get_payment_search_filters

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 5.0


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
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            date = None
    else:
        date = None
    funds = request.args.get("funds", None)
    return dict(
        date=date,
        funds=funds,
    )

def get_payment_pagination(**kwargs):
    return Pagination(
        bs_version=4,
        link_size="sm",
        show_single_page=True,
        record_name="payments",
        total=get_payment_count(get_payment_search_filters(**kwargs), **kwargs),
        per_page_parameter="limit",
        page_parameter="page",
        **kwargs
    )

def get_payments(rows):
    return [get_payment(row) for row in rows]

def get_payment(row):
    return get_scheme_data(row, ROOT_SCHEME)

def get_report(rows):
    data = []
    headers = []

    for key, value in REPORT_SCHEME.items():
        headers.append(value["title"])

    for row in rows:
        item = []
        for key, scheme in REPORT_SCHEME.items():
            value = get_scheme_value(row, scheme) or ""
            item.append(value)
        data.append(item)

    data.insert(0, headers)

    return data
