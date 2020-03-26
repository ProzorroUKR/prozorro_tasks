from flask_restx import reqparse, inputs

from environment_settings import LIQPAY_SANDBOX_BY_DEFAULT_ENABLED

parser_query = reqparse.RequestParser()
parser_query.add_argument("sandbox", type=inputs.boolean, default=inputs.boolean(LIQPAY_SANDBOX_BY_DEFAULT_ENABLED))
