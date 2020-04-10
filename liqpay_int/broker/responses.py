from flask_restx import fields

from liqpay_int.broker.examples import (
    EXAMPLE_CHECKOUT_RESPONSE_CHECKOUT_URL,
    EXAMPLE_CHECKOUT_RESPONSE_ORDER_ID,
)
from liqpay_int.responses import model_response_success, model_response_detailed_error

from liqpay_int.codes import (
    CODE_VALIDATION_ERROR,
    CODE_LIQPAY_API_ERROR,
    CODE_PAYMENT_INVALID,
    CODE_PAYMENT_COMPLAINT_NOT_FOUND,
    CODE_PAYMENT_COMPLAINT_INVALID_CODE,
    CODE_PAYMENT_COMPLAINT_INVALID_VALUE,
    CODE_PAYMENT_COMPLAINT_INVALID_STATUS,
)


model_response_checkout_fields = {
    "url_checkout": fields.String(required=True, example=EXAMPLE_CHECKOUT_RESPONSE_CHECKOUT_URL),
    "order_id": fields.String(required=True, example=EXAMPLE_CHECKOUT_RESPONSE_ORDER_ID),
}

model_response_sign_fields = {
    "signature": fields.String(required=True),
}

model_response_error_checkout_fields = {
    "code": fields.String(example=CODE_VALIDATION_ERROR, enum=[
        CODE_VALIDATION_ERROR,
        CODE_LIQPAY_API_ERROR,
        CODE_PAYMENT_INVALID,
        CODE_PAYMENT_COMPLAINT_NOT_FOUND,
        CODE_PAYMENT_COMPLAINT_INVALID_CODE,
        CODE_PAYMENT_COMPLAINT_INVALID_VALUE,
        CODE_PAYMENT_COMPLAINT_INVALID_STATUS,
    ]),
}

model_response_error_receipt_fields = {
    "code": fields.String(example=CODE_VALIDATION_ERROR, enum=[
        CODE_VALIDATION_ERROR,
        CODE_LIQPAY_API_ERROR,
    ]),
}

model_response_checkout = model_response_success.clone(
    "ResponseCheckout", model_response_checkout_fields
)

model_response_sign = model_response_success.clone(
    "ResponseSign", model_response_sign_fields
)

model_response_checkout_error = model_response_detailed_error.clone(
    "ResponseCheckoutError", model_response_error_checkout_fields
)

model_response_receipt_error = model_response_detailed_error.clone(
    "ResponseReceiptError", model_response_error_receipt_fields
)
