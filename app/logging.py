import logging

from flask import request

from app.auth import auth
from app.utils import get_remote_addr


def app_logging_extra(extra=None):
    try:
        request_extra = {
            "USER": auth.username(),
            "CURRENT_URL": request.url,
            "CURRENT_PATH": request.path,
            "REMOTE_ADDR": get_remote_addr(request),
            "USER_AGENT": request.user_agent,
            "REQUEST_METHOD": request.method,
            "CLIENT_REQUEST_ID": request.headers.get("X-Client-Request-ID", ""),
        }
        if extra is not None:
            extra.update(request_extra)
        else:
            extra = request_extra
        return extra
    except RuntimeError:
        pass



class AppLogger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        custom_extra = app_logging_extra()
        if custom_extra is not None:
            if extra is not None:
                extra.update(custom_extra)
            else:
                extra = custom_extra
        return super(AppLogger,self).makeRecord(
            name, level, fn, lno, msg, args, exc_info,
            func=func, extra=extra, sinfo=sinfo
        )
