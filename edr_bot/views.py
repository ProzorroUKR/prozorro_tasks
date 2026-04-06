from flask import Blueprint
from flask_restx._http import HTTPStatus
from flask_restx import Api, representations

from app.utils import set_output_status
from edr_bot.exceptions import abort_json
from app.resources import Resource as BaseResource
from environment_settings import SANDBOX_MODE
from payments.context import get_string_param
from requests.exceptions import ReadTimeout, ConnectTimeout
from app.logging import getLogger
from app.auth import auth, USERS, login_group_required

logger = getLogger()

bp = Blueprint('edr_integration', __name__)

API_VERSION_MAJOR = 2
API_VERSION_MINOR = 0
API_PREFIX = "/"

api = Api(
    bp,
    prefix=API_PREFIX,
    doc=API_PREFIX,
    version='%s.%s' % (API_VERSION_MAJOR, API_VERSION_MINOR),
    title='Prozorro EDR API',
    description='Prozorro EDR Integration API.',
    authorizations={"basicAuth": {"type": "basic"}},
)


@api.route("/verify")
class VerifyResource(BaseResource):

    dispatch_decorators = [login_group_required("edr")]
    
    @api.doc(description="Get EDR subject data", security="basicAuth")
    @api.param("passport", description="EDR subject passport (if code is not provided)", _in="query")
    @api.param("code", description="EDR subject code", _in="query")
    def get(self):
        from edr_bot.utils import cached_data, get_edr_subject_data, form_edr_response, get_sandbox_data

        # Default parameter name is "code"
        param_name = "code"
        code = get_string_param(param_name)

        # If code is not provided, try to use "passport" as parameter name
        if not code:
            param_name = "passport"
            code = get_string_param("passport")

        # If neither code nor passport is provided, return an error
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

        # Return fake data for sandbox mode if real data if we reached request limit in test api
        if SANDBOX_MODE and response.status_code == 402:
            return get_sandbox_data(code, role)

        # Process EDR API response
        data = form_edr_response(response, code, role)

        # Return processed data
        return data


@api.representation("application/json")
def output_json(data, code, headers=None):
    data = set_output_status(data, code)
    return representations.output_json(data, code, headers=headers)
