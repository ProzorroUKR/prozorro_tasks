from flask_restx._http import HTTPStatus
from werkzeug.exceptions import HTTPException


class InternalServerErrorHTTPException(HTTPException):
    code = HTTPStatus.INTERNAL_SERVER_ERROR


class TransactionsQuantityServerErrorHTTPException(InternalServerErrorHTTPException):
    description = "Successful transactions statuses quantity more than transactions quantity at all"


class DocumentServiceForbiddenError(HTTPException):
    code = HTTPStatus.FORBIDDEN


class DocumentServiceError(HTTPException):
    pass


class ApiServiceError(HTTPException):
    pass
