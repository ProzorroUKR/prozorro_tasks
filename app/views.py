from flask import Blueprint, render_template

bp = Blueprint('app_views', __name__, template_folder="templates")


@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')
