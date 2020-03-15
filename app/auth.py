import os
from hashlib import sha512
from configparser import ConfigParser
from functools import wraps

from flask_httpauth import HTTPBasicAuth
from flask import request
from six import text_type

from app.exceptions import UnauthorizedError, NotAllowedIPError
from app.settings import APP_AUTH_FILE, APP_AUIP_FILE, APP_AUIP_ENABLED, APP_AUIP_HEADER

auth = HTTPBasicAuth()

config = ConfigParser()
config.read(APP_AUTH_FILE or "{}/auth.ini".format(os.path.dirname(os.path.abspath(__file__))), encoding="utf-8")
users = {
    username: dict(password=password, group=group)
    for group in config.sections()
    for username, password in config.items(group)
}

ip_config = ConfigParser()
ip_config.read(APP_AUIP_FILE or "{}/auip.ini".format(os.path.dirname(os.path.abspath(__file__))), encoding="utf-8")
ips = {
    ip: dict(username=username, group=group)
    for group in ip_config.sections()
    for username, ips in ip_config.items(group)
    for ip in ips.split(",")
}


def get_remote_addr(req):
    if APP_AUIP_HEADER:
        return req.headers.get(APP_AUIP_HEADER)
    return request.remote_addr


@auth.verify_password
def verify_password(username, password):
    if username in users:
        if isinstance(password, text_type):
            password = password.encode("utf-8")
        return users[username]['password'] == sha512(password).hexdigest()
    return False


def login_group_required(g):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            res = auth.login_required(f)(*args, **kwargs)
            if hasattr(res, "status_code") and res.status_code == 401:
                raise UnauthorizedError()
            if users[auth.username()]["group"] != g:
                raise UnauthorizedError()
            return f(*args, **kwargs)
        return decorated
    return decorator


def ip_group_required(g):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if APP_AUIP_ENABLED:
                remote_addr = get_remote_addr(request)
                if remote_addr not in ips or ips[remote_addr]["group"] != g:
                    raise NotAllowedIPError()
            return f(*args, **kwargs)
        return decorated
    return decorator
