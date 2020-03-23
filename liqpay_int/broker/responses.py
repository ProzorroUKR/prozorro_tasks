from flask_restx import fields

from liqpay_int.broker.examples import EXAMPLE_CHECKOUT_RESPONSE_CHECKOUT_URL
from liqpay_int.responses import model_response_success

model_response_checkout_fields = {
    "url_checkout": fields.String(example=EXAMPLE_CHECKOUT_RESPONSE_CHECKOUT_URL),
}

model_response_checkout = model_response_success.clone(
    "ResponseCheckout", model_response_checkout_fields
)
