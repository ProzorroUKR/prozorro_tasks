from werkzeug.exceptions import HTTPException


class LiqpayResponseFailureError(HTTPException):
    code = 400
    description = (
        "Liqpay response failure"
    )



class LiqpayResponseError(HTTPException):
    code = 400
    description = (
        "Liqpay response error"
    )

    def __init__(self, description=None, response=None, liqpay_err_description=None):
        if liqpay_err_description is not None:
            description = "{}: {}".format(
                description or LiqpayResponseError.description,
                liqpay_err_description
            )
        super(LiqpayResponseError, self).__init__(
            description=description,
            response=response
        )


class ProzorroApiError(HTTPException):
    code = 400
    description = (
        "Prozorro API request error"
    )


class PaymentInvalidError(HTTPException):
    code = 400
    description = (
        "Payment not recognized according to description provided"
    )


class PaymentComplaintNotFoundError(HTTPException):
    code = 400
    description = (
        "Payment complaint not found"
    )


class PaymentComplaintInvalidCodeError(HTTPException):
    code = 400
    description = (
        "Payment complaint invalid code"
    )


class PaymentComplaintInvalidValueError(HTTPException):
    code = 400
    description = (
        "Payment complaint invalid value"
    )


class PaymentComplaintInvalidStatusError(HTTPException):
    code = 400
    description = (
        "Payment complaint invalid status"
    )
