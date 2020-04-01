import logging

from flask_restx import resource
from werkzeug.exceptions import HTTPException

from app.logging import app_logging_extra

logger = logging.getLogger()


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
                logger.info("%s %s" % (
                    e.data.get("message", ""),
                    str(e.data.get("errors", {}))
                ), extra=app_logging_extra())
            elif hasattr(e, "description"):
                logger.info(e.description, extra=app_logging_extra())
            raise
