import os

from ipaddress import ip_address, ip_network
from hashlib import sha512
from configparser import ConfigParser
from functools import wraps

from flask_httpauth import HTTPBasicAuth
from flask import request
from six import text_type

from app.exceptions import UnauthorizedError, NotAllowedIPError
from app.utils import get_auth_users, get_auth_ips, generate_auth_id
from environment_settings import APP_AUTH_FILE, APP_AUIP_FILE, APP_AUIP_ENABLED

auth = HTTPBasicAuth()

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

config = ConfigParser()
config.read(APP_AUTH_FILE or "{}/auth.ini".format(BASE_PATH), encoding="utf-8")

ip_config = ConfigParser()
ip_config.read(APP_AUIP_FILE or "{}/auip.ini".format(BASE_PATH), encoding="utf-8")

USERS = get_auth_users(config)
IPS = get_auth_ips(ip_config)


@auth.verify_password
def verify_password(username, password):
    user_id = generate_auth_id(username, auth.hash_password_callback(password))
    if user_id in USERS:
        return user_id

@auth.hash_password
def hash_password(password):
    if isinstance(password, text_type):
        password = password.encode("utf-8")
    return sha512(password).hexdigest()


def login_group_required(group):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):

            authorization = auth.get_auth()

            if request.method != 'OPTIONS':
                user_id = auth.authenticate(authorization, None)
                if not user_id or group not in USERS.get(user_id, None).get("groups", []):
                    raise UnauthorizedError(scheme=auth.scheme, realm=auth.realm)

            return func(*args, **kwargs)
        return decorated
    return decorator


def ip_group_required(group):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):

            if APP_AUIP_ENABLED:
                for network_id, network_data in IPS.items():
                    network = network_data.get("network")

                    if ip_address(request.remote_addr) not in ip_network(network):
                        continue
                    if group in network_data.get("groups"):
                        break
                    else:
                        raise NotAllowedIPError()

                else:
                    raise NotAllowedIPError()

            return func(*args, **kwargs)
        return decorated
    return decorator
