import io
from datetime import timedelta

from flask import Blueprint, render_template, redirect, url_for, abort, make_response, request

from app.auth import login_groups_required, COUNTERPARTIES
from autoclient_payments.enums import TransactionStatus, TransactionKind, TransactionType
from autoclient_payments.health import health
from autoclient_payments.message_ids import (
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
)
from autoclient_payments.tasks import process_tender, process_payment_data
from autoclient_payments.results_db import (
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
from autoclient_payments.views.context import (
    get_payment_search_params,
    get_payment_pagination,
    get_report,
    get_payments,
    get_payment,
    get_report_params,
    get_request_params,
    get_int_param,
    YES_NO_CHOICES,
)
from autoclient_payments.data import (
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
    OTHER_COUNTERPARTIES,
)
from autoclient_payments.utils import (
    store_payments_registry_fake,
    generate_report_file,
    generate_report_filename,
    generate_report_title,
    get_payments_registry_fake,
    dumps_payments_registry_fake,
    transactions_list,
    PB_QUERY_DATE_FORMAT,
)
from environment_settings import PB_AUTOCLIENT_RELEASE_DATE, AUTOCLIENT_PROCESSING_ENABLED
from tasks_utils.datetime import get_now, parse_dt_string

bp = Blueprint("autoclient_payments_views", __name__, template_folder="../templates")

bp.add_app_template_filter(date_representation, "date_representation")
bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_message_list_status, "payment_message_list_status")
bp.add_app_template_filter(complaint_status_description, "complaint_status_description")
bp.add_app_template_filter(complaint_reject_description, "complaint_reject_description")
bp.add_app_template_filter(complaint_funds_description, "complaint_funds_description")


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
        "autoclient_payments/payment_list.html",
        rows=rows,
        pagination=get_payment_pagination(total=total, page=page, limit=limit),
        total=total,
        counterparties_choices=list(COUNTERPARTIES.keys()) + [OTHER_COUNTERPARTIES],
        type_choices=TransactionType.as_dict(),
        **search_kwargs,
        **report_kwargs,
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

        min_date = parse_dt_string(PB_AUTOCLIENT_RELEASE_DATE).date()
        max_date = get_now().date()

        return render_template(
            "autoclient_payments/payment_stats.html",
            counts=counts,
            min_date=min_date,
            max_date=max_date,
            counterparties_choices=list(COUNTERPARTIES.keys()) + [OTHER_COUNTERPARTIES],
            type_choices=TransactionType.as_dict(),
            **search_kwargs,
            **report_kwargs,
        )
    else:
        date_from = get_now() - timedelta(days=30)
        date_to = get_now()
        return redirect(
            url_for(
                "autoclient_payments_views.payment_stats",
                date_oper_from=date_from.strftime("%Y-%m-%d"),
                date_oper_to=date_to.strftime("%Y-%m-%d"),
            )
        )


@bp.route("/request", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def payment_request():
    kwargs = get_request_params()
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    status = kwargs.get("status")
    saved = kwargs.get("saved")
    rows = []
    fake_registry = None
    if date_from and date_to:
        registry_date_from = date_from
        registry_date_to = date_to + timedelta(days=1)
        fake_registry = get_payments_registry_fake(registry_date_from, registry_date_to)
        if fake_registry is not None:
            transactions = fake_registry
        else:
            transactions = list(
                transactions_list(
                    start_date=date_from.strftime(PB_QUERY_DATE_FORMAT),
                    end_date=date_to.strftime(PB_QUERY_DATE_FORMAT),
                )
            )
        if transactions:
            for transaction in transactions:
                transaction_status = transaction["PR_PR"]
                if status is not None and transaction_status != status:
                    continue
                item = find_payment_item(transaction) or {}
                if saved is not None and saved != bool(item):
                    continue
                rows.append(
                    {
                        "status": TransactionStatus(transaction_status).name,
                        "transaction": transaction,
                        "item": item.get("payment"),
                        "uid": item.get("_id"),
                        "created": item.get("createdAt"),
                        "updated": item.get("updatedAt"),
                    }
                )
    return render_template(
        "autoclient_payments/payment_request.html",
        rows=rows,
        fake=fake_registry is not None,
        status_choices=TransactionStatus.as_dict(),
        saved_choices=YES_NO_CHOICES,
        TransactionKind=TransactionKind,
        TransactionStatus=TransactionStatus,
        **kwargs,
    )


@bp.route("/request/fake", methods=["POST", "GET"])
@login_groups_required(["admins"])
def payment_request_fake():
    if request.method == "GET":
        text = dumps_payments_registry_fake() or ""
        return render_template("autoclient_payments/payment_fake.html", text=text)
    else:
        store_payments_registry_fake(request.form.get("text"))
        return redirect(url_for("autoclient_payments_views.payment_request_fake"))


@bp.route("/add", methods=["POST"])
@login_groups_required(["admins"])
def payment_add():
    data = request.form
    created_obj = None
    # save and process only real, recorded transactions
    if data.get("FL_REAL") == TransactionKind.REAL.value and data.get("PR_PR") == TransactionStatus.RECORDED.value:
        created_obj = save_payment_item(data, "manual")
    # process only credit transactions
    if AUTOCLIENT_PROCESSING_ENABLED and created_obj and data.get("TRANTYPE") == TransactionType.CREDIT.value:
        uid = str(created_obj.inserted_id)
        return redirect(url_for("autoclient_payments_views.payment_retry", uid=uid))
    else:
        return redirect(request.referrer)


@bp.route("/update", methods=["POST"])
@login_groups_required(["admins"])
def payment_update():
    data = request.form
    if "uid" in data:
        uid = data.get("uid")
        update_payment_item(uid, data)
    return redirect(request.referrer or url_for("autoclient_payments_views.payment_request"))


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
    if (
        params
        and primary_message
        and primary_message.get("message_id")
        not in [
            PAYMENTS_INVALID_PATTERN,
            PAYMENTS_SEARCH_INVALID_COMPLAINT,
            PAYMENTS_SEARCH_INVALID_CODE,
        ]
    ):
        from autoclient_payments.cached import get_tender, get_complaint

        complaint = get_complaint(params)
        tender = get_tender(params)
    else:
        complaint = None
        tender = None
    return render_template(
        "autoclient_payments/payment_detail.html",
        row=row,
        complaint=complaint,
        tender=tender,
        TransactionType=TransactionType,
    )


@bp.route("/<uid>/retry", methods=["GET"])
@login_groups_required(["admins"])
def payment_retry(uid):
    data = get_payment_item(uid)
    if not data:
        abort(404)
    payment = data.get("payment", {})
    if AUTOCLIENT_PROCESSING_ENABLED and payment.get("TRANTYPE") == TransactionType.CREDIT.value:
        process_payment_data.apply_async(kwargs=dict(payment_data=payment))
    return redirect(url_for("autoclient_payments_views.payment_detail", uid=uid))


@bp.route("/<uid>/recheck", methods=["GET"])
@login_groups_required(["admins"])
def payment_recheck(uid):
    data = get_payment_item(uid)
    if not data:
        abort(404)
    params = data.get("params", {})
    tender_id = params.get("tender_id")
    if AUTOCLIENT_PROCESSING_ENABLED and tender_id:
        process_tender.apply_async(kwargs=dict(tender_id=tender_id))
    return redirect(url_for("autoclient_payments_views.payment_detail", uid=uid))


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
        return redirect(
            url_for(
                "autoclient_payments_views.report",
                date_resolution_from=date.strftime("%Y-%m-%d"),
                date_resolution_to=date.strftime("%Y-%m-%d"),
            )
        )
    return render_template("autoclient_payments/payment_report.html", rows=rows, **kwargs)


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
        return redirect(url_for("autoclient_payments_views.status", days=1))
    data = health()
    return render_template("autoclient_payments/payment_status.html", rows=data)
