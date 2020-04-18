from flask_restx._http import HTTPStatus
from werkzeug.exceptions import HTTPException

from liqpay_int.codes import (
    CODE_LIQPAY_API_ERROR,
    CODE_PAYMENT_INVALID,
    CODE_PAYMENT_COMPLAINT_NOT_FOUND,
    CODE_PAYMENT_COMPLAINT_INVALID_CODE,
    CODE_PAYMENT_COMPLAINT_INVALID_VALUE,
    CODE_PAYMENT_COMPLAINT_INVALID_STATUS,
    CODE_PROZORRO_API_PRECONDITION_FAILED,
)


class BadRequestHTTPException(HTTPException):
    code = HTTPStatus.BAD_REQUEST


class LiqpayResponseErrorHTTPException(BadRequestHTTPException):
    description = "Liqpay response error"

    data = dict(
        message=description,
        code=CODE_LIQPAY_API_ERROR
    )

    def __init__(self, description=None, response=None, liqpay_err_description=None):
        if liqpay_err_description is not None:
            description = "{}: {}".format(
                description or LiqpayResponseErrorHTTPException.description,
                liqpay_err_description
            )
        super(LiqpayResponseErrorHTTPException, self).__init__(
            description=description,
            response=response
        )


class ProzorroApiPreconditionFailedHTTPException(BadRequestHTTPException):
    description = "Prozorro api precondition failed caused by invalid X-Server-Id header"

    data = dict(
        message=description,
        code=CODE_PROZORRO_API_PRECONDITION_FAILED
    )


class PaymentInvalidHTTPException(BadRequestHTTPException):
    description = "Payment not recognized according to description provided"

    data = dict(
        message=description,
        code=CODE_PAYMENT_INVALID
    )


class PaymentComplaintNotFoundHTTPException(BadRequestHTTPException):
    description = "Payment complaint not found"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_NOT_FOUND
    )


class PaymentComplaintInvalidCodeHTTPException(BadRequestHTTPException):
    description = "Payment complaint invalid code"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_CODE
    )


class PaymentComplaintInvalidValueHTTPException(BadRequestHTTPException):
    description = "Payment complaint invalid value"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_VALUE
    )


class PaymentComplaintInvalidStatusHTTPException(BadRequestHTTPException):
    description = "Payment complaint invalid status"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_STATUS
    )


class Base64DecodeHTTPException(BadRequestHTTPException):
    description = "BASE64 decode error"

    data = dict(
        message=description
    )


class JSONDecodeHTTPException(BadRequestHTTPException):
    description = "JSON decode error"

    data = dict(
        message=description
    )
