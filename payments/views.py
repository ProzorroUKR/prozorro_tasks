import requests
from flask import Blueprint, render_template, redirect, url_for

from app.auth import login_group_required
from environment_settings import PUBLIC_API_HOST, API_VERSION
from payments.filters import payment_message_status, payment_primary_message, is_dict
from payments.results_db import get_payment_list, get_payment_item, retry_payment_item

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_primary_message, "payment_primary_message")
bp.add_app_template_filter(is_dict, "is_dict")


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def index():
    rows = list(get_payment_list())
    return render_template("payments/index.html", rows=rows)


@bp.route("/<uid>", methods=["GET"])
@login_group_required("accountants")
def info(uid):
    row = get_payment_item(uid)
    complaint = None
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

    return render_template("payments/info.html", row=row, params=params, complaint=complaint)


@bp.route("/<uid>/retry", methods=["GET"])
@login_group_required("accountants")
def retry(uid):
    row = retry_payment_item(uid)
    return redirect(url_for("payments_views.info", uid=uid))



