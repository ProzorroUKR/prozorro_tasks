from celery.exceptions import TaskError, MaxRetriesExceededError
from requests import ConnectionError, Timeout

from app.auth import login_group_required
from app.logging import getLogger
from payments.tasks import process_payment_data, process_payment_complaint_search, process_payment_complaint_data
from liqpay_int.exceptions import (
    LiqpayResponseError,
    LiqpayResponseFailureError,
    PaymentInvalidError,
    ProzorroApiError,
    PaymentComplaintInvalidCodeError,
    PaymentComplaintInvalidValueError,
    PaymentComplaintNotFoundError,
    PaymentComplaintInvalidStatusError,
)
from liqpay_int.resources import Resource
from liqpay_int.responses import (
    model_response_success,
    model_response_error,
    model_response_failure,
)
from liqpay_int.utils import generate_liqpay_receipt_params, generate_liqpay_checkout_params
from liqpay_int.broker.messages import DESC_CHECKOUT_POST, DESC_TICKET_POST
from liqpay_int.broker.namespaces import api
from liqpay_int.broker.parsers import parser_query
from liqpay_int.broker.models import model_checkout, model_receipt
from liqpay_int.broker.responses import (
    model_response_checkout,
    model_response_checkout_error,
    model_response_receipt_error,
)
from liqpay_int.tasks import process_liqpay_request
from payments.utils import check_complaint_code, check_complaint_value, check_complaint_status

logger = getLogger()


@api.route('/checkout')
class CheckoutResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_CHECKOUT_POST, security="basicAuth")
    @api.marshal_with(model_response_checkout, code=200)
    @api.response(400, 'Bad Request', model_response_checkout_error)
    @api.response(401, 'Unauthorized', model_response_error)
    @api.response(500, 'Internal Server Error', model_response_failure)
    @api.expect(model_checkout, validate=True)
    def post(self):
        """
        Receive a payment link.

        :raises ProzorroApiError: In case of something
        """
        description = api.payload.get("description")

        extra = {"PAYMENT_DESCRIPTION": description}
        logger.info("Payment checkout requested.", extra=extra)

        payment_data = dict(description=description)

        try:
            payment_params = process_payment_data.apply(
                kwargs=dict(payment_data=payment_data)
            ).wait()

            if not payment_params:
                raise PaymentInvalidError()

            search_complaint_data = process_payment_complaint_search.apply(kwargs=dict(
                payment_data=payment_data,
                payment_params=payment_params,
            )).wait()

            if not search_complaint_data:
                raise PaymentComplaintNotFoundError()

            if not check_complaint_code(search_complaint_data, payment_params):
                raise PaymentComplaintInvalidCodeError()

            complaint_params = search_complaint_data.get("params")
            complaint_data = process_payment_complaint_data.apply(kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
            )).wait()

            if not complaint_data:
                raise PaymentComplaintNotFoundError()

            if not check_complaint_status(complaint_data):
                raise PaymentComplaintInvalidStatusError()

            if not check_complaint_value(complaint_data):
                raise PaymentComplaintInvalidValueError()

        except (TaskError, MaxRetriesExceededError, Timeout, ConnectionError):
            logger.error("Payment processing task failed.", extra=extra)
            raise ProzorroApiError()

        sandbox = parser_query.parse_args().get("sandbox")
        params = generate_liqpay_checkout_params(
            api.payload, payment_params, complaint_data, sandbox=sandbox
        )

        try:
            resp_json = process_liqpay_request.apply(
                kwargs=dict(params=params, sandbox=sandbox)
            ).wait()
        except (TaskError, MaxRetriesExceededError, Timeout, ConnectionError):
            logger.error("Liqpay api request failed.", extra=extra)
            raise LiqpayResponseFailureError()

        if resp_json.get("result") != "ok":
            logger.error("Liqpay api request error.", extra=extra)
            raise LiqpayResponseError(
                liqpay_err_description=resp_json.get("err_code")
            )

        return {
            "url_checkout": resp_json.get("url_checkout"),
            "order_id": params.get("order_id")
        }


@api.route('/receipt')
class ReceiptResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_TICKET_POST, security="basicAuth")
    @api.marshal_with(model_response_success, code=200)
    @api.response(400, 'Bad Request', model_response_receipt_error)
    @api.response(401, 'Unauthorized', model_response_error)
    @api.response(500, 'Internal Server Error', model_response_failure)
    @api.expect(model_receipt, validate=True)
    def post(self):
        """
        Receive a receipt.
        """
        order_id = api.payload.get("order_id")

        extra = {"PAYMENT_ORDER_ID": order_id}
        logger.info("Payment receipt requested.", extra=extra)

        sandbox = parser_query.parse_args().get("sandbox")
        params = generate_liqpay_receipt_params(api.payload, sandbox=sandbox)

        try:
            resp_json = process_liqpay_request.apply(
                kwargs=dict(params=params, sandbox=sandbox)
            ).wait()
        except (TaskError, MaxRetriesExceededError, Timeout, ConnectionError):
            logger.error("Liqpay api request failed.", extra=extra)
            raise LiqpayResponseFailureError()

        if resp_json.get("result") != "ok":
            logger.error("Liqpay api request error.", extra=extra)
            raise LiqpayResponseError(
                liqpay_err_description=resp_json.get("err_code")
            )

        return {}
