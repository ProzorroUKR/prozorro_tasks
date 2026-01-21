import os

from ipaddress import ip_address, ip_network
from hashlib import sha512
from configparser import ConfigParser
from functools import wraps

from flask_httpauth import HTTPBasicAuth
from flask import request
from six import text_type

from app.exceptions import UnauthorizedError, NotAllowedIPError
from app.utils import get_auth_users, get_auth_ips, generate_auth_id, get_counterparties
from environment_settings import APP_AUTH_FILE, APP_AUIP_FILE, APP_AUIP_ENABLED, APP_COUNTERPARTIES_FILE

auth = HTTPBasicAuth()

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

config = ConfigParser()
config.read(APP_AUTH_FILE or "{}/auth.ini".format(BASE_PATH), encoding="utf-8")

ip_config = ConfigParser()
ip_config.read(APP_AUIP_FILE or "{}/auip.ini".format(BASE_PATH), encoding="utf-8")

counterparties_config = ConfigParser()
counterparties_config.read(APP_COUNTERPARTIES_FILE or "{}/counterparties.ini".format(BASE_PATH), encoding="utf-8")

USERS = get_auth_users(config)
IPS = get_auth_ips(ip_config)
COUNTERPARTIES = get_counterparties(counterparties_config)


def get_network_data():
    for network_id, network_data in IPS.items():
        network = network_data.get("network")
        if ip_address(request.remote_addr) in ip_network(network):
            return network_data


@auth.verify_password
def verify_password(username, password):
    user_id = generate_auth_id(username, auth.hash_password_callback(password))
    return verify_auth_id(user_id)


@auth.hash_password
def hash_password(password):
    if isinstance(password, text_type):
        password = password.encode("utf-8")
    return sha512(password).hexdigest()


def verify_auth_group(user_id, group):
    if user_id:
        return group in USERS.get(user_id, {}).get("groups")


def verify_auth_id(user_id):
    if user_id in USERS:
        return user_id


def login_groups_required(groups):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):

            authorization = auth.get_auth()

            if request.method != 'OPTIONS':
                user_id = auth.authenticate(authorization, None)
                if not any([verify_auth_group(user_id, group) for group in groups]):
                    raise UnauthorizedError(scheme=auth.scheme, realm=auth.realm)

            return func(*args, **kwargs)
        return decorated
    return decorator


def login_group_required(group):
    return login_groups_required([group])


def ip_group_required(group):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):

            if APP_AUIP_ENABLED:
                network_data = get_network_data()
                if not network_data or (network_data and group not in network_data.get("groups")):
                    raise NotAllowedIPError()

            return func(*args, **kwargs)
        return decorated
    return decorator
