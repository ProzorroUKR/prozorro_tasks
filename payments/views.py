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
from liqpay_int.tasks import process_payment_data
from payments.results_db import (
    get_payment_item,
    query_combined_or,
    query_payment_report_success,
    query_payment_report_failed,
    save_payment_item,
    find_payment_item,
    update_payment_item,
    get_payment_results,
    query_payment_results,
    get_payment_stats,
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
from payments.settings import RELEASE_2020_04_19
from payments.utils import (
    get_payments_registry,
    store_payments_registry_fake,
    generate_report_file,
    generate_report_filename,
    generate_report_title,
    get_payments_registry_fake,
    dumps_payments_registry_fake,
)
from tasks_utils.datetime import get_now, parse_dt_string

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
    search_kwargs = get_payment_search_params()

    page = search_kwargs.get("page")
    limit = search_kwargs.get("limit")

    resolution_date_from = report_kwargs.get("date_resolution_from")
    resolution_date_to = report_kwargs.get("date_resolution_to")
    date_from = resolution_date_from
    date_to = resolution_date_to + timedelta(days=1) if resolution_date_to else None

    filters = query_payment_results(date_from, date_to, **search_kwargs)

    data = get_payment_results(filters, page=page, limit=limit)

    results = data["results"]
    meta = data["meta"]
    total = meta["total"]

    rows = get_payments(results)

    return render_template(
        "payments/payment_list.html",
        rows=rows,
        pagination=get_payment_pagination(
            total=total,
            page=page,
            limit=limit
        ),
        total=total,
        **search_kwargs,
        **report_kwargs
    )


@bp.route("/stats", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_stats():
    report_kwargs = get_report_params()
    search_kwargs = get_payment_search_params()

    resolution_date_from = report_kwargs.get("date_resolution_from")
    resolution_date_to = report_kwargs.get("date_resolution_to")

    payment_date_from = search_kwargs.get("payment_date_from")
    payment_date_to = search_kwargs.get("payment_date_to")

    if payment_date_from and payment_date_to:
        date_from = resolution_date_from
        date_to = resolution_date_to + timedelta(days=1) if resolution_date_to else None

        filters = query_payment_results(date_from, date_to, **search_kwargs)

        data = get_payment_stats(filters)

        counts = data["counts"]

        min_date = parse_dt_string(RELEASE_2020_04_19).date()
        max_date = get_now().date()

        return render_template(
            "payments/payment_stats.html",
            counts=counts,
            min_date=min_date,
            max_date=max_date,
            **search_kwargs,
            **report_kwargs
        )
    else:
        date_from = get_now() - timedelta(days=30)
        date_to = get_now()
        return redirect(url_for(
            "payments_views.payment_stats",
            date_oper_from=date_from.strftime("%Y-%m-%d"),
            date_oper_to=date_to.strftime("%Y-%m-%d")
        ))


@bp.route("/request", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_request():
    kwargs = get_request_params()
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    rows = []
    fake_registry = None
    if date_from and date_to:
        registry_date_from = date_from
        registry_date_to = date_to + timedelta(days=1)
        fake_registry = get_payments_registry_fake(registry_date_from, registry_date_to)
        if fake_registry:
            registry = fake_registry
        else:
            registry = get_payments_registry(registry_date_from, registry_date_to)
        if registry:
            for message in registry.get("messages", []):
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
        text = dumps_payments_registry_fake() or ""
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
        registry_date_from = datetime.strptime(data.get("date_from"), "%Y-%m-%d")
        registry_date_to = datetime.strptime(data.get("date_to"), "%Y-%m-%d") + timedelta(days=1)
        fake_registry = get_payments_registry_fake(registry_date_from, registry_date_to)
        if fake_registry:
            registry = fake_registry
        else:
            registry = get_payments_registry(registry_date_from, registry_date_to)
        if registry and registry.get("messages") is not None:
            for message in registry.get("messages"):
                item = find_payment_item(message) or {}
                payment_status = message.pop("status", None)
                if payment_status and payment_status == "success" and item.get("payment") != message:
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
        data_success_filters = query_payment_report_success(
            resolution_exists=True,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
        data_failed_filters = query_payment_report_failed(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        filters = query_combined_or([data_success_filters, data_failed_filters])
        data = get_payment_results(filters)["results"]
        rows = get_report(data, total=True)
    else:
        date = get_now() - timedelta(days=1)
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
        filters = query_payment_report_success(
            resolution_exists=True,
            resolution_funds=funds,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
    elif funds in [FUNDS_UNKNOWN]:
        filters = query_payment_report_failed(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
    elif funds in [FUNDS_ALL]:
        rows = list()
        filters_success = query_payment_report_success(
            resolution_exists=True,
            resolution_date_from=date_from,
            resolution_date_to=date_to,
        )
        filters_failed = query_payment_report_failed(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
            message_ids_date_from=date_from,
            message_ids_date_to=date_to,
        )
        filters = query_combined_or([filters_success, filters_failed])
    else:
        abort(404)
        return

    rows = get_payment_results(filters)["results"]
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
