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
    DESC_PAYMENT_SOURCE,
)

model_payment_fields = {
    "description": fields.String(description=DESC_PAYMENT_DESC),
    "amount": fields.String(description=DESC_PAYMENT_AMOUNT),
    "currency": fields.String(description=DESC_PAYMENT_CURR),
    "date_oper": fields.String(description=DESC_PAYMENT_DATE_OPER),
    "type": fields.String(description=DESC_PAYMENT_TYPE),
    "source": fields.String(description=DESC_PAYMENT_SOURCE),
    "account": fields.String(description=DESC_PAYMENT_ACC),
    "okpo": fields.String(description=DESC_PAYMENT_OKPO),
    "mfo": fields.String(description=DESC_PAYMENT_MFO),
    "name": fields.String(description=DESC_PAYMENT_NAME),
}

model_payment = Model(
    "ModelPayment", model_payment_fields
)
