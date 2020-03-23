from flask_restx import Model, fields

from liqpay_int.provider.messages import (
    DESC_PAYMENT_TYPE,
    DESC_PAYMENT_DATE_OPER,
    DESC_PAYMENT_AMOUNT,
    DESC_PAYMENT_CURR,
    DESC_PAYMENT_ACC,
    DESC_PAYMENT_OKPO,
    DESC_PAYMENT_MFO,
    DESC_PAYMENT_NAME,
    DESC_PAYMENT_DESC,
)

model_payment_fields = {
    "type": fields.String(required=True, description=DESC_PAYMENT_TYPE),
    "date_oper": fields.String(required=True, description=DESC_PAYMENT_DATE_OPER),
    "amount": fields.String(required=True, description=DESC_PAYMENT_AMOUNT),
    "currency": fields.String(required=True, description=DESC_PAYMENT_CURR),
    "account": fields.String(required=True, description=DESC_PAYMENT_ACC),
    "okpo": fields.String(required=True, description=DESC_PAYMENT_OKPO),
    "mfo": fields.String(required=True, description=DESC_PAYMENT_MFO),
    "name": fields.String(required=True, description=DESC_PAYMENT_NAME),
    "description": fields.String(required=True, description=DESC_PAYMENT_DESC),
}

model_payment = Model(
    "ModelPayment", model_payment_fields
)
