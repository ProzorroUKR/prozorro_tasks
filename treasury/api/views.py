from flask import Blueprint, request
from treasury.api.methods.method_factory import MethodFactory
from treasury.api.auth import verify_auth
from treasury.api.parsers.base import RequestFields
from treasury.api.builders import XMLResponse
from app.logging import getLogger

logger = getLogger()

bp = Blueprint('treasury', __name__)


@bp.route("", methods=('POST',))
def main():
    xml_parser = RequestFields(request.data)
    fields = xml_parser.parse()
    if not verify_auth(fields.UserLogin, fields.UserPassword):
        return XMLResponse(code="10", message="Invalid login or password", status=403)
    handler = MethodFactory.create(fields.MethodName)
    logger.info(f'DataSign: {fields.DataSign}')
    result = handler(fields.Data, fields.MessageId).run()
    return result



