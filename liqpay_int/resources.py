from flask_restx import resource
from werkzeug.exceptions import HTTPException

from app.logging import getLogger
from liqpay_int.codes import CODE_VALIDATION_ERROR

logger = getLogger()


class Resource(resource.Resource):

    dispatch_decorators = []

    def dispatch_request(self, *args, **kwargs):
        meth = super(Resource, self).dispatch_request
        for decorator in self.dispatch_decorators:
            meth = decorator(meth)
        return meth(*args, **kwargs)

    def validate_payload(self, *args, **kwargs):
        try:
            super(Resource, self).validate_payload(*args, **kwargs)
        except HTTPException as e:
            if hasattr(e, "data"):
                e.data["code"] = CODE_VALIDATION_ERROR
                logger.info("%s %s" % (e.data.get("message"), e.data.get("errors")))
            raise
