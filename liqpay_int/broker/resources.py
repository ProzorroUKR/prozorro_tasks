from binascii import Error as ASCIIError
from json import JSONDecodeError

from flask import request
from flask_restx import abort, marshal
from flask_restx._http import HTTPStatus
from requests import ConnectionError, Timeout

from app.auth import login_group_required
from app.logging import getLogger
from liqpay_int.broker.utils import get_cookies
from liqpay_int.exceptions import (
    LiqpayResponseErrorHTTPException,
    PaymentInvalidHTTPException,
    PaymentComplaintInvalidCodeHTTPException,
    PaymentComplaintInvalidValueHTTPException,
    PaymentComplaintNotFoundHTTPException,
    PaymentComplaintInvalidStatusHTTPException,
    Base64DecodeHTTPException,
    JSONDecodeHTTPException,
    ProzorroApiPreconditionFailedHTTPException,
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
from liqpay_int.broker.messages import (
    DESC_CHECKOUT_POST,
    DESC_TICKET_POST,
    DESC_SIGNATURE_POST,
    SERVER_ID_DESC,
    REQUEST_ID_DESC,
    CLIENT_REQUEST_ID_DESC,
)
from liqpay_int.broker.namespaces import api
from liqpay_int.broker.parsers import parser_query
from liqpay_int.broker.models import model_checkout, model_receipt, model_sign
from liqpay_int.broker.responses import (
    model_response_checkout,
    model_response_checkout_error,
    model_response_receipt_error,
    model_response_sign,
)
from payments.utils import (
    check_complaint_code,
    check_complaint_value,
    check_complaint_status,
    get_payment_params,
    request_complaint_search,
    request_complaint_data,
)

logger = getLogger()


@api.route('/checkout')
class CheckoutResource(Resource):

    dispatch_decorators = [login_group_required("brokers")]

    @api.doc(description=DESC_CHECKOUT_POST, security="basicAuth")
    @api.doc_response(HTTPStatus.BAD_REQUEST, model=model_response_checkout_error)
    @api.doc_response(HTTPStatus.UNAUTHORIZED, model=model_response_error)
    @api.doc_response(HTTPStatus.SERVICE_UNAVAILABLE, model=model_response_failure)
    @api.doc_response(HTTPStatus.INTERNAL_SERVER_ERROR, model=model_response_failure)
    @api.param("X-Server-ID", description=SERVER_ID_DESC, _in="header")
    @api.param("X-Request-ID", description=REQUEST_ID_DESC, _in="header")
    @api.param("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC, _in="header")
    @api.header("X-Request-ID", description=REQUEST_ID_DESC)
    @api.header("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC)
    @api.marshal_with(model_response_checkout, code=HTTPStatus.OK)
    @api.expect(model_checkout, validate=True)
    def post(self):
        """
        Receive a payment link.
        """
        data = marshal(api.payload, model_checkout, skip_none=True)
        description = data.get("description", "")
        extra = {"PAYMENT_DESCRIPTION": description}
        logger.info("Payment checkout requested.", extra=extra)
        payment_data = dict(description=description)
        server_id = request.headers.get("X-Server-ID")
        try:
            payment_params = get_payment_params(description)
            if not payment_params:
                raise PaymentInvalidHTTPException()

            complaint_pretty_id = payment_params.get("complaint")
            cookies = {"SERVER_ID": server_id} if server_id else get_cookies()

            response = request_complaint_search(complaint_pretty_id, cookies=cookies)
            if response.status_code == 412:
                raise ProzorroApiPreconditionFailedHTTPException()
            if response.status_code != 200:
                raise PaymentComplaintNotFoundHTTPException()

            search_complaints_data = response.json()["data"]
            if len(search_complaints_data) == 0:
                raise PaymentComplaintNotFoundHTTPException()

            search_complaint_data = search_complaints_data[0]
            if not check_complaint_code(search_complaint_data, payment_params):
                raise PaymentComplaintInvalidCodeHTTPException()

            complaint_params = search_complaint_data.get("params", {})
            tender_id = complaint_params.get("tender_id")
            item_type = complaint_params.get("item_type")
            item_id = complaint_params.get("item_id")
            complaint_id = complaint_params.get("complaint_id")

            response = request_complaint_data(
                tender_id=tender_id,
                item_type=item_type,
                item_id=item_id,
                complaint_id=complaint_id,
                cookies=cookies
            )
            if response.status_code == 412:
                raise ProzorroApiPreconditionFailedHTTPException()
            if response.status_code != 200:
                raise PaymentComplaintNotFoundHTTPException()

            complaint_data = response.json()["data"]

            if not check_complaint_status(complaint_data):
                raise PaymentComplaintInvalidStatusHTTPException()
            if not check_complaint_value(complaint_data):
                raise PaymentComplaintInvalidValueHTTPException()

        except (Timeout, ConnectionError):
            abort(code=HTTPStatus.SERVICE_UNAVAILABLE)
        else:
            sandbox = parser_query.parse_args().get("sandbox")
            params = generate_liqpay_checkout_params(
                data, payment_params, complaint_data, sandbox=sandbox
            )
            try:
                resp_json = liqpay_request(data=params, sandbox=sandbox)
            except (Timeout, ConnectionError):
                logger.warning("Liqpay api request failed.", extra=extra)
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
    @api.param("X-Request-ID", description=REQUEST_ID_DESC, _in="header")
    @api.param("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC, _in="header")
    @api.header("X-Request-ID", description=REQUEST_ID_DESC)
    @api.header("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC)
    @api.expect(model_receipt, validate=True)
    def post(self):
        """
        Receive a receipt.
        """
        data = marshal(api.payload, model_receipt, skip_none=True)
        order_id = data.get("order_id")
        extra = {"PAYMENT_ORDER_ID": order_id}
        logger.info("Payment receipt requested.", extra=extra)
        sandbox = parser_query.parse_args().get("sandbox")
        params = generate_liqpay_receipt_params(data, sandbox=sandbox)
        try:
            resp_json = liqpay_request(data=params, sandbox=sandbox)
        except (Timeout, ConnectionError):
            logger.warning("Liqpay api request failed.", extra=extra)
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
    @api.param("X-Request-ID", description=REQUEST_ID_DESC, _in="header")
    @api.param("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC, _in="header")
    @api.header("X-Request-ID", description=REQUEST_ID_DESC)
    @api.header("X-Client-Request-ID", description=CLIENT_REQUEST_ID_DESC)
    @api.expect(model_sign, validate=True)
    def post(self):
        """
        Receive a signature.
        """
        data = marshal(api.payload, model_sign, skip_none=True)
        logger.info("Payment signature requested.")
        sandbox = parser_query.parse_args().get("sandbox")
        original_data = data.get("data")
        try:
            liqpay_data = liqpay_decode(original_data, sandbox=sandbox)
        except ASCIIError:
            raise Base64DecodeHTTPException()
        except JSONDecodeError:
            raise JSONDecodeHTTPException()
        signature = liqpay_sign(original_data, sandbox=sandbox)
        return {'signature': signature}
