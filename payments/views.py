from flask import Blueprint, render_template, redirect, url_for

from app.auth import login_group_required
from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS, PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
)
from payments.results_db import get_payment_list, get_payment_item, retry_payment_item

bp = Blueprint("payments_views", __name__, template_folder="templates")


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def index():
    rows = list(get_payment_list())
    return render_template("payments/index.html", rows=rows)


@bp.route("/<uid>", methods=["GET"])
@login_group_required("accountants")
def info(uid):
    row = get_payment_item(uid)
    return render_template("payments/info.html", row=row)



@bp.route("/<uid>/retry", methods=["GET"])
@login_group_required("accountants")
def retry(uid):
    row = retry_payment_item(uid)
    return redirect(url_for("payments_views.info", uid=uid))


PAYMENTS_SUCCESS_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
]

PAYMENTS_DANGER_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
]

PAYMENTS_WARNING_MESSAGE_ID_LIST = [
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
]


@bp.app_template_filter("payment_primary_message")
def payment_primary_message(payment):
    primary_list = []
    primary_list.extend(PAYMENTS_SUCCESS_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_DANGER_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_WARNING_MESSAGE_ID_LIST)
    for primary in primary_list:
        for message in payment.get("messages", []):
            if message.get("message_id") == primary:
                return message


@bp.app_template_filter("payment_message_status")
def payment_message_status(message):
    if message is None:
        return None
    message_id = message.get("message_id")
    if message_id in PAYMENTS_SUCCESS_MESSAGE_ID_LIST:
        return "success"
    elif message_id in PAYMENTS_DANGER_MESSAGE_ID_LIST:
        return "warning"
    elif message_id in PAYMENTS_WARNING_MESSAGE_ID_LIST:
        return "danger"
    return None
