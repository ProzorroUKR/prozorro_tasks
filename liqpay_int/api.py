import sys

from flask import Blueprint
from flask_restx import Api, reqparse, inputs

from liqpay_int.provider.namespaces import api as provider_ns
from liqpay_int.broker.namespaces import api as broker_ns
from liqpay_int.resources import Resource
from payments.health import health, save_health_data, get_health_data
from payments.results_db import init_indexes
from autoclient_payments.results_db import init_indexes as init_autoclient_indexes

API_VERSION_MAJOR = 1
API_VERSION_MINOR = 0
API_PREFIX = "/api/v{}".format(API_VERSION_MAJOR)

if "test" not in sys.argv[0]:  # pragma: no cover
    init_indexes()
    init_autoclient_indexes()

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
    parser_query_healthcheck = reqparse.RequestParser()
    parser_query_healthcheck.add_argument(
        "historical",
        type=inputs.boolean,
        default=False
    )

    def get(self):
        data = health()
        save_health_data(data)
        if self.parser_query_healthcheck.parse_args().get("historical"):
            historical_list = get_health_data()
            data["historical"] = [{
                "data": item["data"],
                "timestamp": int(item["createdAt"].timestamp() * 1000)
            } for item in historical_list]
        if data["status"] != "available":
            return data, 500
        return data


import liqpay_int.representations
