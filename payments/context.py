import requests
from flask import request, url_for
from flask_paginate import Pagination

from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.results_db import get_payment_count

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10

CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 2.0


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
    if exclude:
        args = {key: value for key, value in args.items() if value and key not in exclude}
    if include:
        args.update(**include)
    args = {key: value for key, value in args.items() if value}
    return url_for(endpoint, **args)


def get_payment_search_params():
    try:
        page = int(request.args.get('page', DEFAULT_PAGE))
    except ValueError:
        page = DEFAULT_PAGE
    try:
        limit = int(request.args.get('limit', DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT
    payment_type = request.args.get('type', None)
    query = request.args.get('query', None)
    return dict(
        limit=limit,
        page=page,
        payment_type=payment_type,
        search=query
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
