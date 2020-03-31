import os
from hashlib import sha512
from configparser import ConfigParser
from functools import wraps

from flask_httpauth import HTTPBasicAuth
from flask import request
from six import text_type

from app.exceptions import UnauthorizedError, NotAllowedIPError
from app.settings import APP_AUTH_FILE, APP_AUIP_FILE, APP_AUIP_ENABLED
from app.utils import get_auth_users, get_auth_ips, get_remote_addr

auth = HTTPBasicAuth()

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

config = ConfigParser()
config.read(APP_AUTH_FILE or "{}/auth.ini".format(BASE_PATH), encoding="utf-8")
users = get_auth_users(config)

ip_config = ConfigParser()
ip_config.read(APP_AUIP_FILE or "{}/auip.ini".format(BASE_PATH), encoding="utf-8")
ips = get_auth_ips(ip_config)


@auth.verify_password
def verify_password(username, password):
    if username in users:
        if isinstance(password, text_type):
            password = password.encode("utf-8")
        return users[username]["password"] == sha512(password).hexdigest()
    return False


def login_group_required(g):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            res = auth.login_required(f)(*args, **kwargs)
            if hasattr(res, "status_code") and res.status_code == 401:
                raise UnauthorizedError(scheme=auth.scheme, realm=auth.realm)
            if users[auth.username()]["group"] != g:
                raise UnauthorizedError(scheme=auth.scheme, realm=auth.realm)
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
