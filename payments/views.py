import io
import json
import shelve
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, abort, make_response, request

from app.auth import login_groups_required
from payments.health import health
from payments.message_ids import (
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
)
from payments.tasks import process_payment_data
from payments.results_db import (
    get_payment_list,
    get_payment_item,
    get_combined_filters_or,
    get_payment_search_filters,
    get_payment_report_success_filters,
    get_payment_report_failed_filters,
    get_combined_filters_and,
    get_payment_count,
    save_payment_item,
    find_payment_item,
    PAYMENT_STATUS_FIELD,
    update_payment_item,
)
from payments.context import (
    url_for_search,
    get_payment_search_params,
    get_payment_pagination,
    get_report,
    get_payments,
    get_payment,
    get_report_params,
    get_request_params,
    get_int_param,
)
from payments.data import (
    PAYMENTS_FAILED_MESSAGE_ID_LIST,
    PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
    complaint_status_description,
    complaint_reject_description,
    complaint_funds_description,
    payment_message_list_status,
    payment_message_status,
    date_representation,
    payment_primary_message,
)
from payments.utils import (
    get_payments_registry,
    store_payments_registry,
    generate_report_file,
    generate_report_filename,
    generate_report_title,
    STATUS_MAIN_PAYMENT_FAKE,
    MAIN_PAYMENT_STATUS_FIELD,
    MAIN_PAYMENT_MESSAGES_FIELD,
)

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(date_representation, "date_representation")
bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_message_list_status, "payment_message_list_status")
bp.add_app_template_filter(complaint_status_description, "complaint_status_description")
bp.add_app_template_filter(complaint_reject_description, "complaint_reject_description")
bp.add_app_template_filter(complaint_funds_description, "complaint_funds_description")

bp.add_app_template_global(url_for_search, "url_for_search")


@bp.route("/", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_list():
    report_kwargs = get_report_params()
    date_from = report_kwargs.get("date_resolution_from")
    date_to = report_kwargs.get("date_resolution_to")
    data_success_filters = get_payment_report_success_filters(
        resolution_date_from=date_from,
        resolution_date_to=date_to,
    )
    data_failed_filters = get_payment_report_failed_filters(
        message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
        message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
        message_ids_date_from=date_from,
        message_ids_date_to=date_to,
    )
    report_filters = get_combined_filters_or([data_success_filters, data_failed_filters])

    search_kwargs = get_payment_search_params()
    search_filters = get_payment_search_filters(**search_kwargs)

    filters = get_combined_filters_and([search_filters, report_filters])

    rows = list(get_payment_list(filters, **search_kwargs, **report_kwargs))
    total = get_payment_count(filters, **search_kwargs, **report_kwargs)
    data = get_payments(rows)
    return render_template(
        "payments/payment_list.html",
        rows=data,
        pagination=get_payment_pagination(
            total=total,
            **search_kwargs,
            **report_kwargs
        ),
        total=total,
        **search_kwargs,
        **report_kwargs
    )


@bp.route("/request", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_request():
    kwargs = get_request_params()
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    rows = []
    fake = False
    if date_from and date_to:
        data = get_payments_registry(date_from, date_to)
        if data and data.get(MAIN_PAYMENT_MESSAGES_FIELD) is not None:
            fake = data.get(MAIN_PAYMENT_STATUS_FIELD) == STATUS_MAIN_PAYMENT_FAKE
            for message in data.get(MAIN_PAYMENT_MESSAGES_FIELD):
                item = find_payment_item(message) or {}
                status = message.pop(PAYMENT_STATUS_FIELD, None)
                rows.append({
                    "message": message,
                    "item": item.get("payment"),
                    "uid": item.get("_id"),
                    "status": status
                })
    return render_template(
        "payments/payment_request.html",
        rows=rows,
        fake=fake,
        **kwargs
    )


@bp.route("/request/fake", methods=["POST", "GET"])
@login_groups_required(["admins"])
def payment_request_fake():
    if request.method == "GET":
        with shelve.open('payments.db') as db:
            return render_template(
                "payments/payment_fake.html",
                        text=json.dumps(db['registry'], indent=4, ensure_ascii=False)
            )
    else:
        store_payments_registry(request.form.get("text"))
        return redirect(url_for("payments_views.payment_request_fake"))


@bp.route("/add", methods=["POST"])
@login_groups_required(["admins"])
def payment_add():
    data = request.form
    result = save_payment_item(data, "manual")
    if result is not None:
        uid = result.inserted_id
        return redirect(url_for("payments_views.payment_detail", uid=uid))
    else:
        return redirect(request.referrer or url_for("payments_views.payment_request"))


@bp.route("/update", methods=["POST"])
@login_groups_required(["admins"])
def payment_update():
    data = request.form
    uid = data.get("uid")
    result = update_payment_item(uid, data)
    if result is not None:
        return redirect(url_for("payments_views.payment_detail", uid=uid))
    else:
        return redirect(request.referrer or url_for("payments_views.payment_request"))


@bp.route("/<uid>", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_detail(uid):
    data = get_payment_item(uid)
    if not data:
        abort(404)
    row = get_payment(data)
    params = data.get("params", None)
    messages = data.get("messages", [])
    primary_message = payment_primary_message(messages)
    if params and primary_message and primary_message.get("message_id") not in [
        PAYMENTS_INVALID_PATTERN,
        PAYMENTS_SEARCH_INVALID_COMPLAINT,
        PAYMENTS_SEARCH_INVALID_CODE,
    ]:
        from payments.cached import get_tender, get_complaint
        complaint = get_complaint(params)
        tender = get_tender(params)
    else:
        complaint = None
        tender = None
    return render_template(
        "payments/payment_detail.html",
        row=row,
        complaint=complaint,
        tender=tender,
    )


@bp.route("/<uid>/retry", methods=["GET"])
@login_groups_required(["admins"])
def payment_retry(uid):
    data = get_payment_item(uid)
    if not data:
        abort(404)
    payment = data.get("payment", {})
    if payment.get("type") == "credit":
        process_payment_data.apply_async(kwargs=dict(
            payment_data=payment
        ))
    return redirect(url_for("payments_views.payment_detail", uid=uid))


@bp.route("/report", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def report():
    kwargs = get_report_params()
    date_from = kwargs.get("date_resolution_from")
    date_to = kwargs.get("date_resolution_to")
    if date_from and date_to:
        data_success_filters = get_payment_report_success_filters(
            resolution_exists=True,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
        data_failed_filters = get_payment_report_failed_filters(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        filters = get_combined_filters_or([data_success_filters, data_failed_filters])
        data = list(get_payment_list(filters))
        rows = get_report(data)
    else:
        date = datetime.now() - timedelta(days=1)
        return redirect(url_for(
            "payments_views.report",
            date_resolution_from=date.strftime("%Y-%m-%d"),
            date_resolution_to=date.strftime("%Y-%m-%d")
        ))
    return render_template(
        "payments/payment_report.html",
        rows=rows,
        **kwargs
    )


@bp.route("/report/download", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def report_download():
    kwargs = get_report_params()
    date_from = kwargs.get("date_resolution_from")
    date_to = kwargs.get("date_resolution_to")
    funds = kwargs.get("funds") or "all"

    if not date_from and not date_to:
        abort(404)
        return

    if funds in ["state", "complainant"]:
        filters = get_payment_report_success_filters(
            resolution_exists=True,
            resolution_funds=funds,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
    elif funds in ["unknown"]:
        filters = get_payment_report_failed_filters(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        rows = list(get_payment_list(filters))
    elif funds in ["all"]:
        rows = list()
        filters_success = get_payment_report_success_filters(
            resolution_exists=True,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
        filters_failed = get_payment_report_failed_filters(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        filters = get_combined_filters_or([filters_success, filters_failed])
    else:
        abort(404)
        return

    rows = list(get_payment_list(filters))
    data = get_report(rows)
    bytes_io = io.BytesIO()
    title = generate_report_title(date_from, date_to, funds)
    generate_report_file(bytes_io, data, title)
    filename = generate_report_filename(date_from, date_to, funds)
    response = make_response(bytes_io.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response


@bp.route("/status", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def status():
    days = get_int_param("days", default=0)
    if not days:
        return redirect(url_for("payments_views.status", days=1))
    data = health()
    return render_template(
        "payments/payment_status.html",
        rows=data
    )
