from liqpay_int.namespaces import Namespace
from liqpay_int.provider.models import model_payment
from liqpay_int.responses import (
    model_response_success,
    model_response_detailed_error,
    model_response_error,
    model_response_failure,
)

api = Namespace(
    "provider",
    description="Provider related operations.",
    path="/"
)

api.models[model_payment.name] = model_payment
api.models[model_response_success.name] = model_response_success
api.models[model_response_detailed_error.name] = model_response_detailed_error
api.models[model_response_error.name] = model_response_error
api.models[model_response_failure.name] = model_response_failure

import liqpay_int.provider.resources
