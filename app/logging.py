import logging
from functools import wraps

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
            custom_extra["REQUEST_ID"] = request.environ.get("X_REQUEST_ID", "")
            custom_extra["CLIENT_REQUEST_ID"] = request.environ.get("X_CLIENT_REQUEST_ID", "")
            custom_extra["HTTP_X_FORWARDED_FOR"] = request.environ.get("HTTP_X_FORWARDED_FOR", "")
            custom_extra["HTTP_X_FORWARDED_PROTO"] = request.environ.get("HTTP_X_FORWARDED_PROTO", "")

        extra = kwargs.setdefault("extra", self.extra or {})
        for key in custom_extra: extra.setdefault(key, custom_extra[key])

        return msg, kwargs


def adaptLogger(logger, adapter):
    return adapter(logger)


def getLogger(name=None):
    return adaptLogger(logging.getLogger(name), AppLoggerAdapter)


def log_exc(logger, exception, message_id):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
            except exception as exc:
                logger.exception(exc, extra={"MESSAGE_ID": message_id})
                raise
            return result
        return wrapped
    return wrapper
