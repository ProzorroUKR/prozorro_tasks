from flask import request, jsonify
from werkzeug.exceptions import HTTPException


class UnauthorizedError(HTTPException):
    def __init__(self, description=None, response=None, scheme=None, realm=None):
        self.scheme = scheme
        self.realm = realm
        request.data  # Clear TCP receive buffer of any pending data
        super(UnauthorizedError, self).__init__(description=description, response=response)

    code = 401
    description = (
        "Invalid username or password"
    )

    def get_headers(self, environ=None):
        headers = super(UnauthorizedError, self).get_headers(environ=environ)
        if self.scheme and self.realm:
            headers.append(("WWW-Authenticate", self.authenticate_header()))
        return headers

    def authenticate_header(self):
        return '{0} realm="{1}"'.format(self.scheme, self.realm)


class NotAllowedIPError(HTTPException):
    code = 403
    description = (
        "Your IP address is not allowed"
    )


def abort_json(code, error_message, headers=None, **extra):
    response = jsonify(error_message, **extra)
    response.status_code = code
    if headers:
        response.headers.update(headers)

    exception = HTTPException(description=error_message)
    exception.code = code
    exception.response = response
    raise exception
