from werkzeug.exceptions import HTTPException


class UnauthorizedError(HTTPException):
    code = 401
    description = (
        "Invalid username or password"
    )


class NotAllowedIPError(HTTPException):
    code = 403
    description = (
        "Your IP address is not allowed"
    )
