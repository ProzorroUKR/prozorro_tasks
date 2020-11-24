from flask import Blueprint, render_template

from app.auth import login_groups_required
from app.utils import (
    typing_is_dict,
    typing_is_list,
    prozorro_api_tender_path,
    prozorro_api_item_path,
    prozorro_api_complaint_path,
    prozorro_portal_tender_path,
    prozorro_api_url,
    prozorro_portal_url,
    url_for_search,
)

bp = Blueprint("app_views", __name__, template_folder="templates")


bp.add_app_template_filter(typing_is_dict, "typing_is_dict")
bp.add_app_template_filter(typing_is_list, "typing_is_list")

bp.add_app_template_filter(prozorro_portal_url, "prozorro_portal_url")
bp.add_app_template_filter(prozorro_portal_tender_path, "prozorro_portal_tender_path")
bp.add_app_template_filter(prozorro_api_url, "prozorro_api_url")
bp.add_app_template_filter(prozorro_api_tender_path, "prozorro_api_tender_path")
bp.add_app_template_filter(prozorro_api_item_path, "prozorro_api_item_path")
bp.add_app_template_filter(prozorro_api_complaint_path, "prozorro_api_complaint_path")

bp.add_app_template_global(url_for_search, "url_for_search")


@bp.route("/", methods=["GET"])
@login_groups_required(["admins", "accountants"])
def index():
    return render_template("index.html")
