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


class PaymentInvalidError(HTTPException):
    code = 400
    description = (
        "Invalid payment data"
    )
