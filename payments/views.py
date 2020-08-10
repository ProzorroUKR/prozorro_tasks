import io
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
    combined_filters_or,
    get_payment_search_filters,
    get_payment_report_success_filters,
    get_payment_report_failed_filters,
    combined_filters_and,
    get_payment_count,
    save_payment_item,
    find_payment_item,
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
    FUNDS_STATE,
    FUNDS_COMPLAINANT,
    FUNDS_UNKNOWN,
    FUNDS_ALL,
)
from payments.utils import (
    get_payments_registry,
    store_payments_registry_fake,
    generate_report_file,
    generate_report_filename,
    generate_report_title,
    get_payments_registry_fake,
    dumps_payments_registry_fake,
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
    resolution_date_from = report_kwargs.get("date_resolution_from")
    resolution_date_to = report_kwargs.get("date_resolution_to")
    date_from = resolution_date_from
    date_to = resolution_date_to + timedelta(days=1) if resolution_date_to else None
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
    report_filters = combined_filters_or([data_success_filters, data_failed_filters])

    search_kwargs = get_payment_search_params()
    search_filters = get_payment_search_filters(**search_kwargs)

    filters = combined_filters_and([search_filters, report_filters])

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
    fake_registry = None
    if date_from and date_to:
        registry_date_from = date_from.date()
        registry_date_to = date_to.date() + timedelta(days=1)
        fake_registry = get_payments_registry_fake(registry_date_from, registry_date_to)
        if fake_registry:
            registry = fake_registry
        else:
            registry = get_payments_registry(registry_date_from, registry_date_to)
        for message in registry.get("messages"):
            item = find_payment_item(message) or {}
            payment_status = message.pop("status", None)
            rows.append({
                "status": payment_status,
                "message": message,
                "item": item.get("payment"),
                "uid": item.get("_id"),
                "created": item.get("createdAt"),
                "updated": item.get("updatedAt"),
            })
    return render_template(
        "payments/payment_request.html",
        rows=rows,
        fake=fake_registry is not None,
        **kwargs
    )


@bp.route("/request/fake", methods=["POST", "GET"])
@login_groups_required(["admins"])
def payment_request_fake():
    if request.method == "GET":
        text = dumps_payments_registry_fake()
        return render_template("payments/payment_fake.html", text=text)
    else:
        store_payments_registry_fake(request.form.get("text"))
        return redirect(url_for("payments_views.payment_request_fake"))


@bp.route("/add", methods=["POST"])
@login_groups_required(["admins"])
def payment_add():
    save_payment_item(request.form, "manual")
    return redirect(request.referrer or url_for("payments_views.payment_request"))


@bp.route("/update", methods=["POST"])
@login_groups_required(["admins"])
def payment_update():
    data = request.form
    if "uid" in data:
        uid = data.get("uid")
        update_payment_item(uid, data)
    elif "date_from" in data and "date_to" in data:
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        registry = get_payments_registry(date_from, date_to)
        if registry and registry.get("messages") is not None:
            for message in registry.get("messages"):
                item = find_payment_item(message) or {}
                payment_status = message.pop("status", None)
                if payment_status and payment_status ==  "success" and item.get("payment") != message:
                    uid = item.get("_id")
                    update_payment_item(uid, message)
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
    date_resolution_from = kwargs.get("date_resolution_from")
    date_resolution_to = kwargs.get("date_resolution_to")
    if date_resolution_from and date_resolution_to:
        date_from = date_resolution_from
        date_to = date_resolution_to + timedelta(days=1)
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
        filters = combined_filters_or([data_success_filters, data_failed_filters])
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
    date_resolution_from = kwargs.get("date_resolution_from")
    date_resolution_to = kwargs.get("date_resolution_to")
    funds = kwargs.get("funds") or "all"

    if not date_resolution_from and not date_resolution_to:
        abort(404)
        return

    date_from = date_resolution_from
    date_to = date_resolution_to + timedelta(days=1)

    if funds in [FUNDS_STATE, FUNDS_COMPLAINANT]:
        filters = get_payment_report_success_filters(
            resolution_exists=True,
            resolution_funds=funds,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
    elif funds in [FUNDS_UNKNOWN]:
        filters = get_payment_report_failed_filters(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        rows = list(get_payment_list(filters))
    elif funds in [FUNDS_ALL]:
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
        filters = combined_filters_or([filters_success, filters_failed])
    else:
        abort(404)
        return

    rows = list(get_payment_list(filters))
    data = get_report(rows, total=True)
    bytes_io = io.BytesIO()
    title = generate_report_title(date_resolution_from, date_resolution_to, funds)
    generate_report_file(bytes_io, data, title)
    filename = generate_report_filename(date_resolution_from, date_resolution_to, funds)
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
