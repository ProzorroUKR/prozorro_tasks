from binascii import Error as ASCIIError
from json import JSONDecodeError

from flask_restx import abort
from flask_restx._http import HTTPStatus
from requests import ConnectionError, Timeout

from app.auth import login_group_required
from app.logging import getLogger
from liqpay_int.broker.utils import get_cookies
from payments.tasks import (
    process_payment_data,
    process_payment_complaint_search,
    process_payment_complaint_data,
)
from liqpay_int.exceptions import (
    LiqpayResponseErrorHTTPException,
    PaymentInvalidHTTPException,
    PaymentComplaintInvalidCodeHTTPException,
    PaymentComplaintInvalidValueHTTPException,
    PaymentComplaintNotFoundHTTPException,
    PaymentComplaintInvalidStatusHTTPException,
    Base64DecodeHTTPException,
    JSONDecodeHTTPException,
)
from liqpay_int.resources import Resource
from liqpay_int.responses import (
    model_response_success,
    model_response_error,
    model_response_failure,
)
from liqpay_int.utils import (
    generate_liqpay_receipt_params, generate_liqpay_checkout_params, liqpay_sign,
    liqpay_decode, liqpay_request,
)
from liqpay_int.broker.messages import DESC_CHECKOUT_POST, DESC_TICKET_POST, DESC_SIGNATURE_POST
from liqpay_int.broker.namespaces import api
from liqpay_int.broker.parsers import parser_query
from liqpay_int.broker.models import model_checkout, model_receipt, model_sign
from liqpay_int.broker.responses import (
    model_response_checkout,
    model_response_checkout_error,
    model_response_receipt_error,
    model_response_sign,
)
from payments.utils import check_complaint_code, check_complaint_value, check_complaint_status

logger = getLogger()


@api.route('/checkout')
class CheckoutResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_CHECKOUT_POST, security="basicAuth")
    @api.doc_response(HTTPStatus.BAD_REQUEST, model=model_response_checkout_error)
    @api.doc_response(HTTPStatus.UNAUTHORIZED, model=model_response_error)
    @api.doc_response(HTTPStatus.SERVICE_UNAVAILABLE, model=model_response_failure)
    @api.doc_response(HTTPStatus.INTERNAL_SERVER_ERROR, model=model_response_failure)
    @api.marshal_with(model_response_checkout, code=HTTPStatus.OK)
    @api.expect(model_checkout, validate=True)
    def post(self):
        """
        Receive a payment link.
        """
        description = api.payload.get("description")

        extra = {"PAYMENT_DESCRIPTION": description}
        logger.info("Payment checkout requested.", extra=extra)

        payment_data = dict(description=description)

        try:
            cookies = get_cookies()

            payment_params = process_payment_data.apply(kwargs=dict(
                payment_data=payment_data,
            )).wait()

            if not payment_params:
                raise PaymentInvalidHTTPException()

            search_complaint_data = process_payment_complaint_search.apply(kwargs=dict(
                payment_data=payment_data,
                payment_params=payment_params,
                cookies=cookies,
            )).wait()

            if not search_complaint_data:
                raise PaymentComplaintNotFoundHTTPException()

            if not check_complaint_code(search_complaint_data, payment_params):
                raise PaymentComplaintInvalidCodeHTTPException()

            complaint_params = search_complaint_data.get("params")
            complaint_data = process_payment_complaint_data.apply(kwargs=dict(
                complaint_params=complaint_params,
                payment_data=payment_data,
                cookies=cookies,
            )).wait()

            if not complaint_data:
                raise PaymentComplaintNotFoundHTTPException()

            if not check_complaint_status(complaint_data):
                raise PaymentComplaintInvalidStatusHTTPException()

            if not check_complaint_value(complaint_data):
                raise PaymentComplaintInvalidValueHTTPException()

        except (Timeout, ConnectionError):
            abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
        else:
            sandbox = parser_query.parse_args().get("sandbox")
            params = generate_liqpay_checkout_params(
                api.payload, payment_params, complaint_data, sandbox=sandbox
            )
            try:
                resp_json = liqpay_request(data=params, sandbox=sandbox)
            except (Timeout, ConnectionError):
                logger.error("Liqpay api request failed.")
                abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                if not resp_json:
                    raise LiqpayResponseErrorHTTPException()
                if resp_json.get("result") != "ok":
                    raise LiqpayResponseErrorHTTPException(liqpay_err_description=resp_json.get("err_code"))
                return {
                    "url_checkout": resp_json.get("url_checkout"),
                    "order_id": params.get("order_id")
                }


@api.route('/receipt')
class ReceiptResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_TICKET_POST, security="basicAuth")
    @api.doc_response(HTTPStatus.BAD_REQUEST, model=model_response_receipt_error)
    @api.doc_response(HTTPStatus.UNAUTHORIZED, model=model_response_error)
    @api.doc_response(HTTPStatus.SERVICE_UNAVAILABLE, model=model_response_failure)
    @api.doc_response(HTTPStatus.INTERNAL_SERVER_ERROR, model=model_response_failure)
    @api.marshal_with(model_response_success, code=HTTPStatus.OK)
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
            resp_json = liqpay_request(data=params, sandbox=sandbox)
        except (Timeout, ConnectionError):
            logger.error("Liqpay api request failed.")
            abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
        else:
            if not resp_json:
                raise LiqpayResponseErrorHTTPException()
            if resp_json.get("result") != "ok":
                raise LiqpayResponseErrorHTTPException(liqpay_err_description=resp_json.get("err_code"))
            return {
                "url_checkout": resp_json.get("url_checkout"),
                "order_id": params.get("order_id")
            }


@api.route('/signature')
class SignatureResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_SIGNATURE_POST, security="basicAuth")
    @api.doc_response(HTTPStatus.BAD_REQUEST, model=model_response_error)
    @api.doc_response(HTTPStatus.UNAUTHORIZED, model=model_response_error)
    @api.doc_response(HTTPStatus.SERVICE_UNAVAILABLE, model=model_response_failure)
    @api.doc_response(HTTPStatus.INTERNAL_SERVER_ERROR, model=model_response_failure)
    @api.marshal_with(model_response_sign, code=HTTPStatus.OK)
    @api.expect(model_sign, validate=True)
    def post(self):
        """
        Receive a signature.
        """
        logger.info("Payment signature requested.")
        sandbox = parser_query.parse_args().get("sandbox")
        try:
            data = liqpay_decode(api.payload.get("data"), sandbox=sandbox)
        except ASCIIError:
            raise Base64DecodeHTTPException()
        except JSONDecodeError:
            raise JSONDecodeHTTPException()
        signature = liqpay_sign(data, sandbox=sandbox)
        return {'signature': signature}
