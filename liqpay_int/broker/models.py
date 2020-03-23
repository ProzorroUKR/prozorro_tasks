from flask_restx import Model, fields

from liqpay_int.broker.examples import (
    EXAMPLE_CHECKOUT_AMOUNT, EXAMPLE_CHECKOUT_CURR, EXAMPLE_CHECKOUT_DESC,
    EXAMPLE_CHECKOUT_LANG,
    EXAMPLE_CHECKOUT_RESULT_URL,
    EXAMPLE_CHECKOUT_SERVER_URL,
    EXAMPLE_CHECKOUT_ORDER_ID,
    EXAMPLE_TICKET_EMAIL,
    EXAMPLE_TICKET_ORDER_ID,
    EXAMPLE_TICKET_LANG,
    EXAMPLE_TICKET_STAMP,
)
from liqpay_int.broker.messages import (
    DESC_CHECKOUT_AMOUNT,
    DESC_CHECKOUT_CURR,
    DESC_CHECKOUT_DESC,
    DESC_CHECKOUT_LANG,
    DESC_CHECKOUT_RESULT_URL,
    DESC_CHECKOUT_SERVER_URL,
    DESC_CHECKOUT_ORDER_ID,
    DESC_TICKET_EMAIL,
    DESC_TICKET_ORDER_ID,
    DESC_TICKET_LANG,
    DESC_TICKET_STAMP,
    DESC_REQUEST_SANDBOX,
)

model_request_fields = {
    "sandbox": fields.String(description=DESC_REQUEST_SANDBOX),
}

model_checkout_fields = {
    "amount": fields.String(required=True, description=DESC_CHECKOUT_AMOUNT, example=EXAMPLE_CHECKOUT_AMOUNT),
    "currency": fields.String(required=True, description=DESC_CHECKOUT_CURR, example=EXAMPLE_CHECKOUT_CURR),
    "description": fields.String(required=True, description=DESC_CHECKOUT_DESC, example=EXAMPLE_CHECKOUT_DESC),
    "language": fields.String(description=DESC_CHECKOUT_LANG, example=EXAMPLE_CHECKOUT_LANG),
    "result_url": fields.String(description=DESC_CHECKOUT_RESULT_URL, example=EXAMPLE_CHECKOUT_RESULT_URL),
    "server_url": fields.String(description=DESC_CHECKOUT_SERVER_URL, example=EXAMPLE_CHECKOUT_SERVER_URL),
    "order_id": fields.String(description=DESC_CHECKOUT_ORDER_ID, example=EXAMPLE_CHECKOUT_ORDER_ID),
}

model_receipt_fields = {
    "email": fields.String(required=True, description=DESC_TICKET_EMAIL, example=EXAMPLE_TICKET_EMAIL),
    "order_id": fields.String(required=True, description=DESC_TICKET_ORDER_ID, example=EXAMPLE_TICKET_ORDER_ID),
    "language": fields.String(required=True, description=DESC_TICKET_LANG, example=EXAMPLE_TICKET_LANG),
    "stamp": fields.Boolean(description=DESC_TICKET_STAMP, example=EXAMPLE_TICKET_STAMP),
}


model_request = Model(
    "ModelRequest", model_request_fields
)

model_checkout = Model(
    "ModelCheckout", model_checkout_fields
)

model_receipt = Model(
    "ModelReceipt", model_receipt_fields
)
