import logging
import flask

from flask import request

from app.auth import auth
from app.utils import get_remote_addr


class AppLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super(AppLoggerAdapter, self).__init__(logger, None)

    def process(self, msg, kwargs):
        custom_extra = {}

        if flask.has_request_context():
            custom_extra["USER"] = auth.username()
            custom_extra["CURRENT_URL"] = request.url
            custom_extra["CURRENT_PATH"] = request.path
            custom_extra["REMOTE_ADDR"] = get_remote_addr(request)
            custom_extra["USER_AGENT"] = request.user_agent
            custom_extra["REQUEST_METHOD"] = request.method
            custom_extra["CLIENT_REQUEST_ID"] = request.headers.get("X-Client-Request-ID", "")

        extra = kwargs.setdefault("extra", self.extra or {})
        for key in custom_extra: extra.setdefault(key, custom_extra[key])

        return msg, kwargs


def getLogger(name=None):
    return AppLoggerAdapter(logging.getLogger(name))
