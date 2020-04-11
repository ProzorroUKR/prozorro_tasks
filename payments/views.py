from flask import Blueprint, render_template, redirect, url_for, abort

from app.auth import login_group_required
from payments.filters import (
    payment_message_status,
    payment_primary_message,
    PAYMENTS_MESSAGE_IDS,
)
from payments.tasks import process_payment_data
from payments.results_db import get_payment_list, get_payment_item
from payments.context import url_for_search, get_payment_search_params, get_pagination, get_tender, get_complaint

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_primary_message, "payment_primary_message")


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def payment_list():
    kwargs = get_payment_search_params()
    return render_template(
        "payments/payment_list.html",
        rows=list(get_payment_list(**kwargs)),
        message_ids=PAYMENTS_MESSAGE_IDS,
        url_for_search=url_for_search,
        pagination=get_pagination(**kwargs)
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
    if not row:
        abort(404)
    params = row.get("params", None)
    complaint = get_complaint(params) if params else None
    tender = get_tender(params) if params else None
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
