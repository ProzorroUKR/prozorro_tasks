import io
import pandas

from flask import Blueprint, render_template, redirect, url_for, abort, send_file, make_response, request
from pandas import isna

from app.auth import login_group_required
from payments.filters import (
    payment_message_status,
    payment_primary_message,
    PAYMENTS_MESSAGE_IDS,
    complaint_status_description,
    complaint_reject_description,
    complaint_funds_description,
)
from payments.tasks import process_payment_data
from payments.results_db import get_payment_list, get_payment_item
from payments.context import (
    url_for_search, get_payment_search_params, get_pagination, get_tender, get_complaint,
    get_report,
    get_payments,
    get_payment,
    get_report_params,
)

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
        pagination=get_pagination(**kwargs)
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
    if date:
        rows = list(get_payment_list(resolution_exists=True, **kwargs))
        data = get_report(rows)
        headers = data.pop(0)
        filename = "{}-{}-report".format(date.date().isoformat(), funds)
        bytes_io = io.BytesIO()
        data_frame = pandas.DataFrame(data, columns=headers, index=range(1, len(data) + 1))
        with pandas.ExcelWriter(bytes_io, engine='xlsxwriter') as writer:
            data_frame.to_excel(writer, sheet_name=filename)
            workbook = writer.book
            worksheet = writer.sheets[filename]
            format = workbook.add_format({'text_wrap': True})
            format.set_align('top')
            for idx, col in enumerate(data_frame):
                series = data_frame[col]
                series_max_nen = series.astype(str).map(len).max()
                name_len = len(str(series.name))
                max_len = max(series_max_nen, name_len) if not isna(series_max_nen) else name_len
                worksheet.set_column(idx + 1, idx + 1, min(max_len, 50), cell_format=format)
        response = make_response(bytes_io.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=%s.xlsx" % filename
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    abort(404)
