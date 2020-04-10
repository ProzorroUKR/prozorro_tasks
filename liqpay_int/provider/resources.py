from flask_restx import abort
from kombu.exceptions import OperationalError
from pymongo.errors import PyMongoError

from app.auth import ip_group_required, get_network_data
from app.logging import getLogger
from liqpay_int.provider.models import model_payment
from liqpay_int.provider.namespaces import api
from liqpay_int.resources import Resource
from liqpay_int.responses import (
    model_response_success,
    model_response_detailed_error,
    model_response_error,
    model_response_failure,
)
from payments.results_db import save_payment_item
from payments.tasks import process_payment_data


logger = getLogger()


@api.route('/push')
class PushResource(Resource):

    dispatch_decorators = [ip_group_required("payment_providers")]

    @api.marshal_with(model_response_success, code=200)
    @api.response(400, 'Bad Request', model_response_detailed_error)
    @api.response(403, 'Forbidden', model_response_error)
    @api.response(503, 'Service Unavailable', model_response_failure)
    @api.response(500, 'Internal Server Error', model_response_failure)
    @api.expect(model_payment, validate=True)
    def post(self):
        extra = {"PAYMENT_DESCRIPTION": api.payload.get("description")}
        try:
            save_payment_item(api.payload, (get_network_data() or {}).get("username"))
            logger.error("Payment save failed.", extra=extra)
        except PyMongoError:
            abort(code=503)
        logger.info("Payment push received.", extra=extra)
        try:
            process_payment_data.apply_async(kwargs=dict(
                payment_data=api.payload
            ))
        except (OperationalError):
            logger.error("Payment send task failed.", extra=extra)
            abort(code=503)
        return {"status": "success"}
