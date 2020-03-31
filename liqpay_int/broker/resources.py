import logging

from celery.exceptions import TaskError
from requests import RequestException

from app.auth import login_group_required
from payments.tasks import process_payment
from liqpay_int.exceptions import LiqpayResponseError, LiqpayResponseFailureError, PaymentInvalidError, ProzorroApiError
from liqpay_int.resources import Resource
from liqpay_int.responses import model_response_success, model_response_error, model_response_failure
from liqpay_int.utils import liqpay_request, generate_liqpay_receipt_params, generate_liqpay_checkout_params
from liqpay_int.broker.messages import DESC_CHECKOUT_POST, DESC_TICKET_POST
from liqpay_int.broker.namespaces import api
from liqpay_int.broker.parsers import parser_query
from liqpay_int.broker.models import model_checkout, model_receipt
from liqpay_int.broker.responses import model_response_checkout


logger = logging.getLogger()


@api.route('/checkout')
class CheckoutResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_CHECKOUT_POST, security="basicAuth")
    @api.marshal_with(model_response_checkout, code=200)
    @api.response(400, 'Bad Request', model_response_error)
    @api.response(401, 'Unauthorized', model_response_error)
    @api.response(500, 'Internal Server Error', model_response_failure)
    @api.expect(model_checkout, validate=True)
    def post(self):
        """
        Receive a payment link.
        """
        description = api.payload.get("description")
        logger.info("Checkout requested.", extra={
            "PAYMENT_DESCRIPTION": description
        })
        try:
            complaint_data = process_payment.apply(
                kwargs=dict(
                    payment_data=dict(description=api.payload.get("description")),
                    return_value=True
                )
            ).wait()
        except (TaskError, RequestException):
            logger.error("Payment processing task failed.", extra={
                "PAYMENT_DESCRIPTION": description
            })
            raise ProzorroApiError()

        if complaint_data:
            args = api.payload
            payment_data = complaint_data.get("payment", {})
            value_data = complaint_data.get("value", {})
            order_id = "{}-{}".format(
                payment_data.get("complaint"),
                payment_data.get("code").upper()
            )
            args.update({
                "order_id": order_id,
                "amount": value_data.get("amount"),
                "currency": value_data.get("currency")
            })
            params = generate_liqpay_checkout_params(args)
            sandbox = parser_query.parse_args().get("sandbox")
            try:
                resp_json = liqpay_request(params=params, sandbox=sandbox)
            except Exception as ex:
                logger.error("Liqpay api request failed.", extra={
                    "PAYMENT_DESCRIPTION": description
                })
                raise LiqpayResponseFailureError()
            else:
                if resp_json.get("result") == "ok":
                    return {
                        "url_checkout": resp_json.get("url_checkout"),
                        "order_id": order_id
                    }
                else:
                    logger.error("Liqpay api request error.", extra={
                        "PAYMENT_DESCRIPTION": description
                    })
                    raise LiqpayResponseError(
                        liqpay_err_description=resp_json.get("err_description")
                    )
        else:
            raise PaymentInvalidError()


@api.route('/receipt')
class ReceiptResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_TICKET_POST, security="basicAuth")
    @api.marshal_with(model_response_success, code=200)
    @api.response(400, 'Bad Request', model_response_error)
    @api.response(401, 'Unauthorized', model_response_error)
    @api.response(500, 'Internal Server Error', model_response_failure)
    @api.expect(model_receipt, validate=True)
    def post(self):
        """
        Receive a receipt.
        """
        order_id = api.payload.get("order_id")
        logger.info("Checkout requested.", extra={
            "PAYMENT_ORDER_ID": order_id
        })
        params = generate_liqpay_receipt_params(api.payload)
        sandbox = parser_query.parse_args().get("sandbox")
        try:
            resp_json = liqpay_request(params=params, sandbox=sandbox)
        except Exception as ex:
            logger.error("Liqpay api request failed.", extra={
                "PAYMENT_ORDER_ID": order_id
            })
            raise LiqpayResponseFailureError()
        else:
            if resp_json.get("result") == "ok":
                return {}
            else:
                logger.error("Liqpay api request error.", extra={
                    "PAYMENT_ORDER_ID": order_id
                })
                raise LiqpayResponseError(
                    liqpay_err_description=resp_json.get("err_description")
                )
