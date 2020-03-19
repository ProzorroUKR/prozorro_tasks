import flask_restplus

from liqpay_int.errors import errors
from liqpay_int.representations import output_json


class RestPlusApi(flask_restplus.Api):
    def __init__(self, *args, **kwargs):
        _errors = errors
        _errors.update(kwargs.get("errors", {}))
        kwargs["errors"] = _errors
        super(RestPlusApi, self).__init__(*args, **kwargs)
        self.representations = {
            "application/json": output_json,
        }
