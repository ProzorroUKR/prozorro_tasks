import sys

from flask import Blueprint
from flask_restx import Api

from liqpay_int.provider.namespaces import api as provider_ns
from liqpay_int.broker.namespaces import api as broker_ns
from liqpay_int.resources import Resource
from payments.health import health
from payments.results_db import init_indexes

API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0
API_PREFIX = "/api/v{}".format(API_VERSION_MAJOR)


if "test" not in sys.argv[0]:  # pragma: no cover
    init_indexes()

bp = Blueprint('payments_resources', __name__)
api = Api(
    bp,
    prefix=API_PREFIX,
    doc=API_PREFIX,
    version='%s.%s' % (API_VERSION_MAJOR, API_VERSION_MINOR),
    title='Liqpay',
    description='Liqpay integration api.'
)

api.add_namespace(broker_ns, path=None)
api.add_namespace(provider_ns, path=None)


@api.route('/healthcheck')
class HealthCheckResource(Resource):

    def get(self):
        health_data = health()
        if health_data["status"] != "available":
            return health_data, 500
        return health_data


import liqpay_int.representations
