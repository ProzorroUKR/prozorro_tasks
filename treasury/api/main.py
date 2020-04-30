from flask import Blueprint, request
from app.auth import verify_auth_group, hash_password, verify_auth_id
from app.utils import generate_auth_id
from treasury.api.parsers.base import RequestFields
from treasury.api.builders import XMLResponse
from treasury.api.methods.method_factory import MethodFactory


bp = Blueprint('treasury', __name__)


@bp.route("", methods=('POST',))
def main():
    xml_parser = RequestFields(request.data)
    fields = xml_parser.parse()
    user_id = generate_auth_id(fields.UserLogin, hash_password(fields.UserPassword))
    if not verify_auth_id(user_id) or not verify_auth_group(user_id, "treasury"):
        return XMLResponse(code="10", message="Invalid login or password", status=403)

    handler = MethodFactory.create(fields.MethodName)
    result = handler(fields.Data, fields.MessageId).run()
    return result
