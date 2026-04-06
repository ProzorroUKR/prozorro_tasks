from flask import Blueprint
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
    from edr_bot.utils import cached_data, get_edr_subject_data, form_edr_response, get_sandbox_data

    # Default parameter name is "code"
    param_name = "code"
    code = get_string_param(param_name)

    # If code is not provided, try to use "passport" as parameter name
    if not code:
        param_name = "passport"
        code = get_string_param("passport")

    # If neither code nor passport is provided, return 403 error
    if not code:
        abort_json(
            code=HTTPStatus.FORBIDDEN,
            error_message={
                "location": "body",
                "name": "data", 
                "description": [{"message": "Wrong name of the GET parameter. Code or passport is required"}],
            },
        )

    # Get user role
    authorization = auth.get_auth()
    user_id = auth.authenticate(authorization, None)
    role = USERS.get(user_id, {}).get("username")

    # Try to get data from cache
    if res := cached_data(code, role):
        return res

    # Try to get data from EDR API
    #  - for "robot" role, it will be paid data ("details" endpoint)
    #  - for normal users, it will be free data ("verify" endpoint)
    try:
        response = get_edr_subject_data(param_name, code)
    except (ReadTimeout, ConnectTimeout):
        abort_json(
            code=HTTPStatus.FORBIDDEN,
            error_message={
                "location": "body",
                "name": "data",
                "description": [{"message": "Gateway Timeout Error"}],
            },
        )

    # Payment is required after request limit is reached for test data
    if SANDBOX_MODE and response.status_code == 402:
        return get_sandbox_data(code, role)

    # process EDR API response
    data = form_edr_response(response, code, role)

    return data
