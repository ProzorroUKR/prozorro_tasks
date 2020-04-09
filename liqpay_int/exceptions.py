from werkzeug.exceptions import HTTPException

from liqpay_int.codes import (
    CODE_LIQPAY_API_FAILURE,
    CODE_LIQPAY_API_ERROR,
    CODE_PROZORRO_API_ERROR,
    CODE_PAYMENT_INVALID,
    CODE_PAYMENT_COMPLAINT_NOT_FOUND,
    CODE_PAYMENT_COMPLAINT_INVALID_CODE,
    CODE_PAYMENT_COMPLAINT_INVALID_VALUE,
    CODE_PAYMENT_COMPLAINT_INVALID_STATUS,
)


class LiqpayResponseFailureHTTPException(HTTPException):
    code = 400
    description = "Liqpay response failure"

    data = dict(
        message=description,
        code=CODE_LIQPAY_API_FAILURE
    )



class LiqpayResponseHTTPException(HTTPException):
    code = 400
    description = "Liqpay response error"

    data = dict(
        message=description,
        code=CODE_LIQPAY_API_ERROR
    )

    def __init__(self, description=None, response=None, liqpay_err_description=None):
        if liqpay_err_description is not None:
            description = "{}: {}".format(
                description or LiqpayResponseHTTPException.description,
                liqpay_err_description
            )
        super(LiqpayResponseHTTPException, self).__init__(
            description=description,
            response=response
        )


class ProzorroApiHTTPException(HTTPException):
    code = 400
    description = "Prozorro API request error"

    data = dict(
        message=description,
        code=CODE_PROZORRO_API_ERROR
    )


class PaymentInvalidHTTPException(HTTPException):
    code = 400
    description = "Payment not recognized according to description provided"

    data = dict(
        message=description,
        code=CODE_PAYMENT_INVALID
    )


class PaymentComplaintNotFoundHTTPException(HTTPException):
    code = 400
    description = "Payment complaint not found"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_NOT_FOUND
    )


class PaymentComplaintInvalidCodeHTTPException(HTTPException):
    code = 400
    description = "Payment complaint invalid code"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_CODE
    )


class PaymentComplaintInvalidValueHTTPException(HTTPException):
    code = 400
    description = "Payment complaint invalid value"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_VALUE
    )


class PaymentComplaintInvalidStatusHTTPException(HTTPException):
    code = 400
    description = "Payment complaint invalid status"

    data = dict(
        message=description,
        code=CODE_PAYMENT_COMPLAINT_INVALID_STATUS
    )


class Base64DecodeHTTPException(HTTPException):
    code = 400
    description = "BASE64 decode error"

    data = dict(
        message=description
    )


class JSONDecodeHTTPException(HTTPException):
    code = 400
    description = "JSON decode error"

    data = dict(
        message=description
    )
