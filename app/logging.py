import logging
import flask

from flask import request

from app.auth import auth


class AppLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super(AppLoggerAdapter, self).__init__(logger, None)

    def process(self, msg, kwargs):
        custom_extra = {}

        if flask.has_request_context():
            custom_extra["USER"] = auth.username()
            custom_extra["CURRENT_URL"] = request.url
            custom_extra["CURRENT_PATH"] = request.path
            custom_extra["REMOTE_ADDR"] = request.remote_addr
            custom_extra["USER_AGENT"] = request.user_agent
            custom_extra["REQUEST_METHOD"] = request.method
            custom_extra["CLIENT_REQUEST_ID"] = request.headers.get("X-Client-Request-ID", "")
            custom_extra["HTTP_X_FORWARDED_FOR"] = request.environ.get('HTTP_X_FORWARDED_FOR', "")
            custom_extra["HTTP_X_FORWARDED_PROTO"] = request.environ.get('HTTP_X_FORWARDED_FOR', "")

        extra = kwargs.setdefault("extra", self.extra or {})
        for key in custom_extra: extra.setdefault(key, custom_extra[key])

        return msg, kwargs


def getLogger(name=None):
    return AppLoggerAdapter(logging.getLogger(name))
