from flask import Blueprint, render_template

from app.auth import login_group_required

bp = Blueprint("app_views", __name__, template_folder="templates")


@bp.route("/", methods=["GET"])
@login_group_required("admins")
def index():
    return render_template("index.html")
