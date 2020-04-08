from flask import Blueprint, render_template

from app.auth import login_group_required
from app.filters import (
    typing_is_dict,
    typing_is_list,
    datetime_astimezone,
    datetime_replace_microseconds,
    datetime_isoformat,
    prozorro_portal_url,
    prozorro_portal_tender_path,
    prozorro_api_url,
    prozorro_api_tender_path,
    prozorro_api_item_path,
    prozorro_api_complaint_path,
)

bp = Blueprint("app_views", __name__, template_folder="templates")


bp.add_app_template_filter(typing_is_dict, "typing_is_dict")
bp.add_app_template_filter(typing_is_list, "typing_is_list")
bp.add_app_template_filter(datetime_astimezone, "datetime_astimezone")
bp.add_app_template_filter(datetime_replace_microseconds, "datetime_replace_microseconds")
bp.add_app_template_filter(datetime_isoformat, "datetime_isoformat")
bp.add_app_template_filter(prozorro_portal_url, "prozorro_portal_url")
bp.add_app_template_filter(prozorro_portal_tender_path, "prozorro_portal_tender_path")
bp.add_app_template_filter(prozorro_api_url, "prozorro_api_url")
bp.add_app_template_filter(prozorro_api_tender_path, "prozorro_api_tender_path")
bp.add_app_template_filter(prozorro_api_item_path, "prozorro_api_item_path")
bp.add_app_template_filter(prozorro_api_complaint_path, "prozorro_api_complaint_path")


@bp.route("/", methods=["GET"])
@login_group_required("admins")
def index():
    return render_template("index.html")
