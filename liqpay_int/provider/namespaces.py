from flask_restx import Namespace

from liqpay_int.provider.models import model_payment
from liqpay_int.responses import model_response_success


api = Namespace(
    "provider",
    description="Provider related operations.",
    path="/"
)

api.models[model_payment.name] = model_payment
api.models[model_response_success.name] = model_response_success

import liqpay_int.provider.resources
