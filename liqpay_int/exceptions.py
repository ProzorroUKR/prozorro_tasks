from werkzeug.exceptions import HTTPException


class LiqpayResponseError(HTTPException):
    code = 400
    description = (
        "Liqpay response error"
    )
