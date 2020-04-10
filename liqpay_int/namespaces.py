import flask_restx


class Namespace(flask_restx.Namespace):
    def doc_response(self, status, model=None, **kwargs):
        description = "%s: %s" % (status.phrase, status.description)
        return super(Namespace, self).response(status.value, description, model=model, **kwargs)
