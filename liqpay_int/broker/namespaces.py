from flask_restx import Namespace

from liqpay_int.responses import (
    model_response_success,
    model_response_error,
    model_response_failure,
    model_response_detailed_error,
)
from liqpay_int.broker.models import model_checkout, model_receipt, model_request
from liqpay_int.broker.responses import (
    model_response_checkout,
    model_response_checkout_error,
    model_response_receipt_error,
)

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
api.models[model_response_detailed_error.name] = model_response_detailed_error
api.models[model_response_failure.name] = model_response_failure
api.models[model_response_checkout.name] = model_response_checkout
api.models[model_response_checkout_error.name] = model_response_checkout_error
api.models[model_response_receipt_error.name] = model_response_receipt_error

import liqpay_int.broker.resources
