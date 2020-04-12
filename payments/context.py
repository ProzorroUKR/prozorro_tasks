import dateutil
import jmespath
import requests
from flask import request, url_for
from flask_paginate import Pagination

from app.filters import datetime_astimezone, datetime_isoformat, datetime_replace_microseconds
from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.filters import complaint_status_description, complaint_reject_description, complaint_funds_description
from payments.results_db import get_payment_count

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10

CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 3.0

DEFAULT_PAYMENT_FIELDS = [
    "description",
    "amount",
    "currency",
    "date_oper",
    "type",
    "account",
    "okpo",
    "mfo",
    "name",
]

payment_scheme = {
    "description": {
        "title": "Призначення платежу",
        "path": "payment.description",
        "default": "",
    },
    "amount": {
        "title": "Сума платежу",
        "path": "payment.amount",
        "default": "",
    },
    "currency": {
        "title": "Валюта платежу",
        "path": "payment.currency",
        "default": "",
    },
    "date_oper": {
        "title": "Дата операції",
        "path": "payment.date_oper",
        "default": "",
    },
    "type": {
        "title": "Тип операції",
        "path": "payment.type",
        "default": "",
    },
    "account": {
        "title": "Номер рахунку",
        "path": "payment.account",
        "default": "",
    },
    "okpo": {
        "title": "ОКПО рахунку",
        "path": "payment.okpo",
        "default": "",
    },
    "mfo": {
        "title": "МФО рахунку",
        "path": "payment.mfo",
        "default": "",
    },
    "name": {
        "title": "Назва рахунку",
        "path": "payment.name",
        "default": "",
    },
}

resolution_scheme = {
    "type": {
        "title": "Рішення по скарзі",
        "path": "resolution.type",
        "method": complaint_status_description,
        "default": "",
    },
    "date": {
        "title": "Дата рішення",
        "path": "resolution.date",
        "default": "",
    },
    "reason": {
        "title": "Причина сказування",
        "path": "resolution.reason",
        "method": complaint_reject_description,
        "default": "",
    },
    "funds": {
        "title": "Висновок",
        "path": "resolution.funds",
        "method": complaint_funds_description,
        "default": "",
    },
}

extra_scheme = {
    "user": {
        "title": "Ініціатор",
        "path": "user",
        "default": "",
    },
    "created": {
        "title": "Дата отримання",
        "path": "createdAt",
        "method": lambda x: datetime_isoformat(datetime_replace_microseconds(datetime_astimezone(x))),
        "default": "",
    },
}

full_scheme = {
    "id": {
        "title": "ID",
        "path": "_id",
        "default": "",
    },
    "payment": {
        "title": "Транзакція",
        "scheme": payment_scheme,
        "default": "",
    },
    "extra": {
        "title": "Додатково",
        "scheme": extra_scheme,
        "default": "",
    },
    "resolution": {
        "title": "Рішення",
        "scheme": resolution_scheme,
        "default": "",
    },
}


def get_scheme_value(data, scheme_info):
    if "scheme" in scheme_info:
        value = {}
        for scheme_nested_field, scheme_nested_info in scheme_info["scheme"].items():
            value.update({scheme_nested_field: get_scheme_item(data, scheme_nested_info)})
        return value
    value = jmespath.search(scheme_info["path"], data) or scheme_info.get("default")
    if "method" in scheme_info:
        value = scheme_info["method"](value)
    return value


def get_scheme_title(data, scheme_info):
    if "title" in scheme_info:
        return scheme_info["title"]
    return None


def get_scheme_item(data, scheme_info):
    value = get_scheme_value(data, scheme_info)
    title = get_scheme_title(data, scheme_info)
    item = dict(value=value)
    if title:
        item.update(dict(title=title))
    return item


def get_scheme_data(data, scheme):
    data_formatted = {}
    for scheme_field, scheme_info in scheme.items():
        data_formatted.update({scheme_field: get_scheme_item(data, scheme_info)})
    return data_formatted

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

def get_pagination(**kwargs):
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
