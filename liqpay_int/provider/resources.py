from datetime import datetime

from flask_restx import abort
from flask_restx._http import HTTPStatus
from kombu.exceptions import OperationalError
from pymongo.errors import PyMongoError

from app.auth import ip_group_required, get_network_data
from app.logging import getLogger
from environment_settings import PB_AUTOCLIENT_RELEASE_DATE
from liqpay_int.broker.messages import REQUEST_ID_DESC, CLIENT_REQUEST_ID_DESC
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
from liqpay_int.tasks import process_payment_data

logger = getLogger()

PAYMENT_DATE_OPER_FORMAT = "%d.%m.%Y %H:%M:%S"


@api.route('/push')
class PushResource(Resource):

    dispatch_decorators = [ip_group_required("payment_providers")]

    @api.doc_response(HTTPStatus.BAD_REQUEST, model=model_response_detailed_error)
    @api.doc_response(HTTPStatus.FORBIDDEN, model=model_response_error)
    @api.doc_response(HTTPStatus.SERVICE_UNAVAILABLE, model=model_response_failure)
    @api.doc_response(HTTPStatus.INTERNAL_SERVER_ERROR, model=model_response_failure)
    @api.param("X-Request-ID", description=REQUEST_ID_DESC, _in="header")
    @api.param("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC, _in="header")
    @api.header("X-Request-ID", description=REQUEST_ID_DESC)
    @api.header("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC)
    @api.marshal_with(model_response_success, code=HTTPStatus.OK)
    @api.expect(model_payment, validate=True)
    def post(self):
        extra = {"PAYMENT_DESCRIPTION": api.payload.get("description")}
        date_release = datetime.fromisoformat(PB_AUTOCLIENT_RELEASE_DATE).date()
        date_oper = datetime.strptime(api.payload.get("date_oper"), PAYMENT_DATE_OPER_FORMAT).date()
        if date_oper >= date_release:
            logger.info("Payment push skipped after autoclient release date.", extra=extra)
            return {"status": "success"}
        try:
            save_payment_item(api.payload, (get_network_data() or {}).get("username"))
        except PyMongoError:
            logger.error("Payment save failed.", extra=extra)
            abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
        logger.info("Payment push received.", extra=extra)
        if api.payload.get("type") == "credit":
            try:
                process_payment_data.apply_async(kwargs=dict(
                    payment_data=api.payload
                ))
            except (OperationalError):
                logger.error("Payment send task failed.", extra=extra)
                abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
        return {"status": "success"}
