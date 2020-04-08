from flask import Blueprint, render_template

from app.auth import login_group_required
from app.filters import is_dict, localize

bp = Blueprint("app_views", __name__, template_folder="templates")


bp.add_app_template_filter(is_dict, "is_dict")
bp.add_app_template_filter(localize, "localize")


@bp.route("/", methods=["GET"])
@login_group_required("admins")
def index():
    return render_template("index.html")
