from flask import Blueprint, request
from app.logging import getLogger
from nazk_bot.api.controllers import get_entity_data_from_nazk

logger = getLogger()

bp = Blueprint('nazk', __name__)


@bp.route("", methods=('POST',))
def get_entity_info_from_nazk():
    pass
