import requests
from flask import Blueprint, render_template, redirect, url_for, request, abort
from flask_paginate import Pagination

from app.auth import login_group_required
from environment_settings import PUBLIC_API_HOST, API_VERSION, PORTAL_HOST
from payments.filters import (
    payment_message_status, payment_primary_message, PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    PAYMENTS_WARNING_MESSAGE_ID_LIST,
    PAYMENTS_DANGER_MESSAGE_ID_LIST,
    PAYMENTS_ERROR_MESSAGE_ID_LIST,
    PAYMENTS_MESSAGE_IDS,
)
from payments.results_db import get_payment_list, get_payment_item, retry_payment_item, get_payment_count

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_primary_message, "payment_primary_message")


DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def payments():
    try:
        page = int(request.args.get('page', DEFAULT_PAGE))
    except ValueError:
        page = DEFAULT_PAGE

    try:
        limit = int(request.args.get('limit', DEFAULT_LIMIT))
    except ValueError:
        limit = DEFAULT_LIMIT

    kwargs = dict(
        limit=limit,
        page=page
    )

    return render_template(
        "payments/payments.html",
        rows=list(get_payment_list(**kwargs)),
        message_ids=PAYMENTS_MESSAGE_IDS,
        pagination=Pagination(
            bs_version=4,
            link_size="sm",
            show_single_page=True,
            record_name="payments",
            total=get_payment_count(),
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
def info(uid):
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
            response = requests.get(url)
        except Exception as exc:
            pass
        else:
            complaint = response.json()["data"]

        url_pattern = "{host}/api/{version}/tenders/{tender_id}"
        url = url_pattern.format(
            host=PUBLIC_API_HOST,
            version=API_VERSION,
            **params
        )
        try:
            response = requests.get(url)
        except Exception as exc:
            pass
        else:
            tender = response.json()["data"]

    return render_template(
        "payments/info.html",
        row=row,
        complaint=complaint,
        tender=tender,
        message_ids=PAYMENTS_MESSAGE_IDS
    )


@bp.route("/<uid>/retry", methods=["GET"])
@login_group_required("accountants")
def retry(uid):
    row = retry_payment_item(uid)
    if not row:
        abort(404)
    return redirect(url_for("payments_views.info", uid=uid))



