import logging

from flask import _request_ctx_stack, request

from app.auth import auth
from app.utils import get_remote_addr


def app_logging_extra():
    ctx = _request_ctx_stack.top
    if ctx is None:
        return {}
    return {
        "USER": auth.username(),
        "CURRENT_URL": request.url,
        "CURRENT_PATH": request.path,
        "REMOTE_ADDR": get_remote_addr(request),
        "USER_AGENT": request.user_agent,
        "REQUEST_METHOD": request.method,
        "CLIENT_REQUEST_ID": request.headers.get("X-Client-Request-ID", ""),
    }



class AppLogger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        custom_extra = app_logging_extra()
        if extra is not None:
            extra.update(custom_extra)
        else:
            extra = custom_extra
        return super(AppLogger,self).makeRecord(
            name, level, fn, lno, msg, args, exc_info,
            func=func, extra=extra, sinfo=sinfo
        )
