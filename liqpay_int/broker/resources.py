from flask_restx import Namespace, Resource

from app.auth import login_group_required
from liqpay_int.broker.messages import DESC_CHECKOUT_POST, DESC_TICKET_POST
from liqpay_int.broker.models import (
    model_checkout,
    model_receipt,
    model_request,
)
from liqpay_int.broker.responses import model_response_checkout
from liqpay_int.exceptions import LiqpayResponseError, LiqpayResponseFailureError, PaymentInvalidError
from liqpay_int.responses import model_response_success, model_response_error, model_response_failure
from liqpay_int.utils import liqpay_request, generate_liqpay_receipt_params, generate_liqpay_checkout_params
from payments.tasks import process_payment

authorizations = {"basicAuth": {"type": "basic"}}

api = Namespace(
    "broker",
    description="Brokers related operations.",
    path="/",
    authorizations=authorizations
)

api.models[model_checkout.name] = model_checkout
api.models[model_receipt.name] = model_receipt
api.models[model_request.name] = model_request

api.models[model_response_success.name] = model_response_success
api.models[model_response_error.name] = model_response_error
api.models[model_response_failure.name] = model_response_failure
api.models[model_response_checkout.name] = model_response_checkout


class CheckoutResource(Resource):

    method_decorators = [login_group_required("brokers")]

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
        complaint_payment_found = process_payment.apply(
            kwargs=dict(
                payment_data=dict(
                    description=api.payload.get("description"),
                    amount=api.payload.get("amount"),
                    currency=api.payload.get("currency"),
                ),
                check_only=True
            )
        ).wait()

        if complaint_payment_found is True:
            params = generate_liqpay_checkout_params(api.payload)
            try:
                resp_json = liqpay_request(params=params, sandbox=False)
            except Exception as ex:
                raise LiqpayResponseFailureError()
            else:
                if resp_json.get("result") == "ok":
                    return {"url_checkout": resp_json.get("url_checkout")}
                else:
                    raise LiqpayResponseError(
                        liqpay_err_description=resp_json.get("err_description")
                    )
        else:
            raise PaymentInvalidError()


class ReceiptResource(Resource):

    method_decorators = [login_group_required("brokers")]

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
        params = generate_liqpay_receipt_params(api.payload)
        try:
            resp_json = liqpay_request(params=params, sandbox=False)
        except Exception as ex:
            raise LiqpayResponseFailureError()
        else:
            if resp_json.get("result") == "ok":
                return {}
            else:
                raise LiqpayResponseError(
                    liqpay_err_description=resp_json.get("err_description")
                )


api.add_resource(CheckoutResource, "/checkout")
api.add_resource(ReceiptResource, "/receipt")
