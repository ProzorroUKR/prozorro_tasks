from flask import jsonify
from flask_restplus import Namespace, Resource

from app.auth import login_group_required
from liqpay_int.broker.parsers import parser_checkout, parser_ticket
from liqpay_int.exceptions import LiqpayResponseError, LiqpayResponseFailureError
from liqpay_int.utils import liqpay_request, generate_liqpay_ticket_params, generate_liqpay_checkout_params

api = Namespace('broker', description='Brokers related operations.', path='/')
api.authorizations = {'basicAuth': {'type': 'basic'}}


class CheckoutResource(Resource):

    method_decorators = [login_group_required("brokers")]

    @api.expect(parser_checkout, validate=True)
    def post(self):
        args = parser_checkout.parse_args(strict=True)
        sandbox = args.pop("sandbox", False)
        params = generate_liqpay_checkout_params(args)
        try:
            resp_json = liqpay_request(params=params, sandbox=sandbox)
        except Exception as ex:
            raise LiqpayResponseFailureError()
        else:
            if resp_json.get("result") == "ok":
                return jsonify({
                    "status": "success",
                    "url_checkout": resp_json.get("url_checkout"),
                })
            else:
                raise LiqpayResponseError(liqpay_err_description=resp_json.get("err_description"))


class TicketResource(Resource):

    method_decorators = [login_group_required("brokers")]

    @api.expect(parser_ticket, validate=True)
    def post(self):
        args = parser_ticket.parse_args(strict=True)
        sandbox = args.pop("sandbox", False)
        params = generate_liqpay_ticket_params(args)
        try:
            resp_json = liqpay_request(params=params, sandbox=sandbox)
        except Exception as ex:
            raise LiqpayResponseFailureError()
        else:
            if resp_json.get("result") == "ok":
                return jsonify({
                    "status": "success",
                })
            else:
                raise LiqpayResponseError(liqpay_err_description=resp_json.get("err_description"))


api.add_resource(CheckoutResource, '/checkout', endpoint="sd")
api.add_resource(TicketResource, '/ticket')
