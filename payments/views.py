import io

from xlsxwriter import Workbook

from flask import Blueprint, render_template, redirect, url_for, abort, make_response

from app.auth import login_group_required
from payments.tasks import process_payment_data
from payments.results_db import get_payment_list, get_payment_item
from payments.context import (
    url_for_search,
    get_payment_search_params,
    get_payment_pagination,
    get_tender,
    get_complaint,
    get_report,
    get_payments,
    get_payment,
    get_report_params,
    PAYMENTS_MESSAGE_IDS,
    payment_primary_message,
    payment_message_status,
)
from payments.data import complaint_status_description, complaint_reject_description, complaint_funds_description

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_primary_message, "payment_primary_message")
bp.add_app_template_filter(complaint_status_description, "complaint_status_description")
bp.add_app_template_filter(complaint_reject_description, "complaint_reject_description")
bp.add_app_template_filter(complaint_funds_description, "complaint_funds_description")


@bp.route("/", methods=["GET"])
@login_group_required("accountants")
def payment_list():
    kwargs = get_payment_search_params()
    rows = list(get_payment_list(**kwargs))
    data = get_payments(rows)
    return render_template(
        "payments/payment_list.html",
        rows=data,
        message_ids=PAYMENTS_MESSAGE_IDS,
        url_for_search=url_for_search,
        pagination=get_payment_pagination(**kwargs)
    )


@bp.route("/<uid>", methods=["GET"])
@login_group_required("accountants")
def payment_detail(uid):
    row = get_payment_item(uid)
    if not row:
        abort(404)
    data = get_payment(row)
    params = row.get("params", None)
    complaint = get_complaint(params) if params else None
    tender = get_tender(params) if params else None
    return render_template(
        "payments/payment_detail.html",
        row=data,
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


@bp.route("/reports", methods=["GET"])
@login_group_required("accountants")
def reports():
    kwargs = get_report_params()
    rows = list(get_payment_list(resolution_exists=True, **kwargs)) if kwargs.get("resolution_date") else []
    data = get_report(rows)
    return render_template(
        "payments/payment_reports.html",
        rows=data,
        url_for_search=url_for_search,
        **kwargs
    )


@bp.route("/reports/download", methods=["GET"])
@login_group_required("accountants")
def reports_download():
    kwargs = get_report_params()
    date = kwargs.get("resolution_date")
    funds = kwargs.get("resolution_funds") or 'all'

    if not date:
        abort(404)

    rows = list(get_payment_list(resolution_exists=True, **kwargs))
    data = get_report(rows)

    for index, row in enumerate(data):
        data[index] = [str(index) if index else " "] + row

    headers = data.pop(0)
    filename = "{}-{}-report".format(date.date().isoformat(), funds)
    bytes_io = io.BytesIO()

    workbook = Workbook(bytes_io)
    worksheet = workbook.add_worksheet()

    properties = {'text_wrap': True}
    cell_format = workbook.add_format(properties)
    cell_format.set_align('top')

    worksheet.add_table(0, 0, len(data), len(headers) - 1, {
        'first_column': True,
        'header_row': True,
        'columns': [{"header": header} for header in headers],
        'data': data
    })

    for index, header in enumerate(headers):
        max_len = max(max(map(lambda x: len(x[index]), data)), len(header))
        worksheet.set_column(index, index, min(max_len + 5, 50), cell_format)

    workbook.close()

    response = make_response(bytes_io.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response
