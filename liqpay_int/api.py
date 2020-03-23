from flask import Blueprint
from flask_restx import Api

from liqpay_int.representations import output_json
from liqpay_int.provider.resources import api as provider_ns
from liqpay_int.broker.resources import api as broker_ns


API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0
API_PREFIX = "/api/v{}".format(API_VERSION_MAJOR)

bp = Blueprint('payments_resources', __name__)
api = Api(
    bp,
    prefix=API_PREFIX,
    doc=API_PREFIX,
    version='%s.%s' % (API_VERSION_MAJOR, API_VERSION_MINOR),
    title='Liqpay',
    description='Liqpay integration api.'
)

api.representations = {
    "application/json": output_json,
}

api.add_namespace(broker_ns, path=None)
api.add_namespace(provider_ns, path=None)
