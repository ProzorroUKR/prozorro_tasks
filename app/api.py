import flask_restful

errors = {
    "InternalServerError": {
        "message": "Something went wrong",
        "status": 500
    },
}


def output_json(data, code, headers=None):
    if code >= 500:
        data["status"] = "failure"
    elif code >= 400:
        data["status"] = "error"
    return flask_restful.output_json(data, code, headers=headers)


class Api(flask_restful.Api):
    def __init__(self, *args, **kwargs):
        _errors = errors
        _errors.update(kwargs.get("errors", {}))
        kwargs["errors"] = _errors
        super(Api, self).__init__(*args, **kwargs)
        self.representations = {
            "application/json": output_json,
        }
