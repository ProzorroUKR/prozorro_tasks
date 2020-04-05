from flask_restx import representations

from app.logging import getLogger
from liqpay_int.api import api

logger = getLogger()

@api.representation("application/json")
def output_json(data, code, headers=None):
    if code >= 500:
        data["status"] = "failure"
    elif code >= 400:
        data["status"] = "error"
        message = data.get("message", "")
        if "errors" in data:
            message += " %s" % str(data.get("errors", {}))
        logger.info(message)
    return representations.output_json(data, code, headers=headers)
