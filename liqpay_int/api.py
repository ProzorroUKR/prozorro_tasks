import sys
from datetime import datetime, timedelta

from flask import Blueprint
from flask_restx import Api, reqparse, inputs

from liqpay_int.provider.namespaces import api as provider_ns
from liqpay_int.broker.namespaces import api as broker_ns
from liqpay_int.resources import Resource
from payments.health import health
from payments.results_db import init_indexes, get_statuses_list, save_status

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
        data = health()
        historical_list = self._get_hist_data_list()
        historical_new = self._save_hist_data(data, historical_list)
        if historical_list:
            if historical_new:
                historical_list = [historical_new] + historical_list
            data["historical"] = [self._generate_hist_item(item) for item in historical_list]
        if data["status"] != "available":
            return data, 500
        return data

    def _generate_hist_item(self, data):
        return {
            "data": data["data"],
            "timestamp": int(data["createdAt"].timestamp())
        }

    def _save_hist_data(self, data, historical):
        if not historical:
            historical = list(get_statuses_list(limit=1))
        if len(historical):
            historical_last = historical[0]
            delta = datetime.now() - historical_last["createdAt"]
            status_changed = False
            for key in historical_last["data"].keys():
                if key != "status":
                    prev_status = historical_last["data"].get(key, {}).get("status")
                    curr_status = data.get(key, {}).get("status")
                    if prev_status != curr_status:
                        status_changed = True
            if delta > timedelta(minutes=10) or status_changed:
                return save_status(data)
        else:
            return save_status(data)

    def _get_hist_data_list(self):
        parser_query_healthcheck = reqparse.RequestParser()
        parser_query_healthcheck.add_argument(
            "historical",
            type=inputs.boolean,
            default=False
        )
        historical_requested = parser_query_healthcheck.parse_args().get("historical")
        if historical_requested:
            historical_list = list(get_statuses_list())
            return historical_list


import liqpay_int.representations
