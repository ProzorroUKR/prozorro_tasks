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
)
from payments.data import (
    complaint_status_description, complaint_reject_description, complaint_funds_description,
    PAYMENTS_MESSAGE_IDS,
    payment_message_list_status,
    payment_message_status,
    PAYMENTS_FAILED_MESSAGE_ID_LIST,
    PAYMENTS_INFO_MESSAGE_ID_LIST,
    PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    PAYMENTS_WARNING_MESSAGE_ID_LIST,
)

bp = Blueprint("payments_views", __name__, template_folder="templates")

bp.add_app_template_filter(payment_message_status, "payment_message_status")
bp.add_app_template_filter(payment_message_list_status, "payment_message_list_status")
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
    data = get_payment_item(uid)
    if not data:
        abort(404)
    row = get_payment(data)
    params = data.get("params", None)
    complaint = get_complaint(params) if params else None
    tender = get_tender(params) if params else None
    return render_template(
        "payments/payment_detail.html",
        row=row,
        complaint=complaint,
        tender=tender,
    )


@bp.route("/<uid>/retry", methods=["GET"])
@login_group_required("admin")
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


@bp.route("/reports", methods=["GET"])
@login_group_required("accountants")
def reports():
    kwargs = get_report_params()
    date = kwargs.get("date")
    funds = kwargs.get("funds")
    if date:
        data_success = list(get_payment_list(
            resolution_exists=True,
            resolution_funds=funds,
            resolution_date=date,
            **kwargs
        ))
        rows_success = get_report(data_success)
        data_failed = list(get_payment_list(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_INFO_MESSAGE_ID_LIST + \
                                PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
                                PAYMENTS_WARNING_MESSAGE_ID_LIST,
            message_ids_date=date,
            **kwargs
        ))
        rows_failed = get_report(data_failed)
        rows = rows_success + rows_failed[1:]
    else:
        rows = []
    return render_template(
        "payments/payment_reports.html",
        rows=rows,
        url_for_search=url_for_search,
        resolution_date=date,
        **kwargs
    )


@bp.route("/reports/download", methods=["GET"])
@login_group_required("accountants")
def reports_download():
    kwargs = get_report_params()
    date = kwargs.get("date")
    funds = kwargs.get("funds") or 'all'

    if not date:
        abort(404)
        return

    if funds in ["state", "complainant"]:
        rows = list(get_payment_list(
            resolution_exists=True,
            resolution_funds=funds,
            resolution_date=date,
        ))
    elif funds in ["unknown"]:
        rows = list(get_payment_list(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_INFO_MESSAGE_ID_LIST + \
                                PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
                                PAYMENTS_WARNING_MESSAGE_ID_LIST,
            message_ids_date=date,
        ))
    elif funds in ["all"]:
        rows = list()
        rows.extend(list(get_payment_list(
            resolution_exists=True,
            resolution_date=date,
        )))
        rows.extend(list(get_payment_list(
            message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
            message_ids_exclude=PAYMENTS_INFO_MESSAGE_ID_LIST + \
                                PAYMENTS_SUCCESS_MESSAGE_ID_LIST + \
                                PAYMENTS_WARNING_MESSAGE_ID_LIST,
            message_ids_date=date,
        )))
    else:
        abort(404)
        return

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
        max_len = max(max(map(lambda x: len(x[index]), data)) if data else 0, len(header))
        worksheet.set_column(index, index, min(max_len + 5, 50), cell_format)

    workbook.close()

    response = make_response(bytes_io.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return response
