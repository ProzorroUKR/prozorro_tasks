import requests
import urllib.parse as urlparse
from flask import Blueprint, render_template, redirect, url_for, request, abort
from flask_paginate import Pagination

from app.auth import login_group_required
from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.filters import (
    payment_message_status,
    payment_primary_message,
    PAYMENTS_MESSAGE_IDS,
)
from payments.tasks import process_payment_data
from payments.results_db import get_payment_list, get_payment_item, get_payment_count

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_primary_message, "payment_primary_message")

CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 2.0

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def payment_list():
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

    kwargs = dict(
        limit=limit,
        page=page,
        payment_type=payment_type,
        search=query,
    )

    def url_for_search(endpoint, exclude=None, include=None):
        encoding = "utf-8"
        query_params = urlparse.parse_qs(request.query_string)
        query_params = {key.decode(encoding): value[0].decode(encoding) for key, value in query_params.items()}
        if exclude:
            query_params = {key: value for key, value in query_params.items() if key not in exclude}
        if include:
            query_params.update(**include)
        return url_for(endpoint, **query_params)

    return render_template(
        "payments/payment_list.html",
        rows=list(get_payment_list(**kwargs)),
        message_ids=PAYMENTS_MESSAGE_IDS,
        url_for_search=url_for_search,
        pagination=Pagination(
            bs_version=4,
            link_size="sm",
            show_single_page=True,
            record_name="payments",
            total=get_payment_count(**kwargs),
            per_page_parameter="limit",
            page_parameter="page",
            **kwargs
        )
    )

@bp.route("/reports", methods=["GET"])
@login_group_required("accountants")
def reports():
    return render_template(
        "payments/reports.html"
    )


@bp.route("/<uid>", methods=["GET"])
@login_group_required("accountants")
def payment_detail(uid):
    row = get_payment_item(uid)
    complaint = None
    tender = None
    if not row:
        abort(404)
    params = row.get("params", None)
    if params:
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

    return render_template(
        "payments/payment_detail.html",
        row=row,
        complaint=complaint,
        tender=tender,
        message_ids=PAYMENTS_MESSAGE_IDS
    )


@bp.route("/<uid>/retry", methods=["GET"])
@login_group_required("accountants")
def payment_retry(uid):
    row = get_payment_item(uid)
    if not row:
        abort(404)
    payment = row.get("payment", {})
    if payment.get("type") == "credit":
        process_payment_data.apply_async(kwargs=dict(
            payment_data=payment
        ))
    return redirect(url_for("payments_views.payment_detail", uid=uid))
