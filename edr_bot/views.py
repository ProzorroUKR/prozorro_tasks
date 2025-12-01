from flask import Blueprint, request
from flask_restx._http import HTTPStatus

from app.exceptions import abort_json
from environment_settings import SANDBOX_MODE
from payments.context import get_string_param
from requests.exceptions import ReadTimeout, ConnectTimeout
from app.logging import getLogger
from app.auth import auth, USERS, login_group_required

logger = getLogger()

bp = Blueprint('edr_integration', __name__)


@bp.route("/verify", methods=('GET',))
@login_group_required("edr")
def verify_edr_code():
    from app.app import cache
    from edr_bot.utils import get_edr_subject_data, form_edr_response, cached_details, get_sandbox_data
    param_name = "code"
    code = get_string_param(param_name)
    if not code:
        param_name = "passport"
        code = get_string_param("passport")
        if not code:
            abort_json(
                code=HTTPStatus.FORBIDDEN,
                error_message={"location": "body", "name": "data",  "description": [{"message": "Wrong name of the GET parameter. Code is required"}]},
            )

    authorization = auth.get_auth()
    user_id = auth.authenticate(authorization, None)
    role = USERS.get(user_id, {}).get("username")

    if role == "robot":
        res = cached_details(request, code)
        if res:
            return res
    elif cached_verify_data := cache.get(f"verify_{code}"):
        logger.info(f"Code {code} was found in cache at verify")
        return cached_verify_data

    logger.info(f'Code {code} was not found in cache at {"details" if role == "robot" else "verify"}')
    try:
        response = get_edr_subject_data(param_name, code)
    except (ReadTimeout, ConnectTimeout):
        abort_json(
            code=HTTPStatus.FORBIDDEN,
            error_message={"location": "body", "name": "data", "description": [{"message": "Gateway Timeout Error"}]},
        )
    if SANDBOX_MODE and response.status_code == 402:  # Payment is required after request limit is reached for test data
        return get_sandbox_data(code, role)
    return form_edr_response(request, response, code, role)
