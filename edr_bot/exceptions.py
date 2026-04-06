from flask import jsonify
from werkzeug.exceptions import HTTPException


def abort_json(code, error_message, headers=None, **extra):
    error_description = {
        "status": "error",
        "errors": [error_message],
    }
    response = jsonify(error_description, **extra)
    response.status_code = code
    if headers:
        response.headers.update(headers)
    exception = HTTPException(description=error_description)
    exception.data = error_description
    exception.code = code
    exception.response = response
    raise exception
