from flask import Blueprint, render_template

from app.auth import login_group_required

bp = Blueprint('payments_views', __name__, template_folder="templates")


@bp.route('/', methods=['GET'])
@login_group_required("accountants")
def index():
    return render_template('payments/index.html')
