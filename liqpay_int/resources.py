from werkzeug.exceptions import HTTPException

from app.logging import getLogger
from app.resources import Resource as BaseResource
from liqpay_int.codes import CODE_VALIDATION_ERROR

logger = getLogger()


class Resource(BaseResource):
    def validate_payload(self, *args, **kwargs):
        try:
            super(Resource, self).validate_payload(*args, **kwargs)
        except HTTPException as e:
            if hasattr(e, "data"):
                e.data["code"] = CODE_VALIDATION_ERROR
                logger.info("%s %s" % (e.data.get("message"), e.data.get("errors")))
            raise
