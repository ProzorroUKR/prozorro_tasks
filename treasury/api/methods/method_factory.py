from flask import abort
from treasury.api.methods.obligation import Obligation
from treasury.api.methods.prtrans import PRTrans
from treasury.api.builders import XMLResponse


class MethodFactory:
    method_types = {
        'PRTrans': PRTrans,
        'Obligation': Obligation
    }

    @classmethod
    def create(cls, method_type):
        method_handler = cls.method_types.get(method_type)
        if method_handler is None:
            return abort(XMLResponse(code="40", message=f"Invalid method: {method_type}", status=400))
        return method_handler
