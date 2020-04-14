import typing
from ipaddress import ip_network

from environment_settings import TIMEZONE, PUBLIC_API_HOST, API_VERSION, PORTAL_HOST

DEFAULT_CONFIG_VALUE_SEPARATOR = ","
DEFAULT_AUTH_ID_SEPARATOR = "_"
DEFAULT_X_FORWARDED_SEPARATOR = ","


def split_config_value(value, separator=DEFAULT_CONFIG_VALUE_SEPARATOR):
    return [item.strip() for item in value.split(separator) if item.strip()]


def generate_auth_id(username, password_hash):
    return DEFAULT_AUTH_ID_SEPARATOR.join([username, password_hash])


def get_auth_users(config):
    users = {}
    for group in config.sections():
        for key, value in config.items(group):
            user_id = generate_auth_id(key, value)
            if user_id not in users:
                groups = get_auth_user_groups(config, key, value)
                user_data = dict(username=key, password=value, groups=groups)
                users[user_id] = user_data
    return users


def get_auth_user_groups(config, username, password):
    groups = []
    for group in config.sections():
        for key, value in config.items(group):
            if key == username and value == password:
                groups.append(group)
    return groups


def get_auth_ips(config):
    ips = {}
    for group in config.sections():
        for key, value in config.items(group):
            for network in split_config_value(value):
                try:
                    ip_network(network)
                except ValueError:
                    raise
                network_id = generate_auth_id(key, network)
                groups = get_auth_ip_groups(config, network, key)
                network_data = dict(username=key, network=network, groups=groups)
                ips[network_id] = network_data
    return ips


def get_auth_ip_groups(config, network, username):
    groups = []
    for group in config.sections():
        for key, value in config.items(group):
            if key == username and network in split_config_value(value):
                groups.append(group)
    return groups


def typing_is_dict(item):
    return isinstance(item, typing.Dict)


def typing_is_list(item):
    return isinstance(item, typing.List)


def datetime_astimezone(dt):
    return dt.astimezone(TIMEZONE)


def datetime_replace_microseconds(dt):
    return dt.replace(microsecond=0)


def datetime_isoformat(dt):
    return dt.isoformat()


def prozorro_api_tender_path(tender_params):
    url_pattern = "/tenders/{tender_id}"
    return url_pattern.format(host=PUBLIC_API_HOST, version=API_VERSION, **tender_params)


def prozorro_api_item_path(item_params):
    url_pattern = "/tenders/{tender_id}/{item_type}/{item_id}"
    return url_pattern.format(host=PUBLIC_API_HOST, version=API_VERSION, **item_params)


def prozorro_api_complaint_path(complaint_params):
    if complaint_params.get("item_type"):
        url_pattern = "/tenders/{tender_id}/{item_type}/{item_id}/complaints/{complaint_id}"
    else:
        url_pattern = "/tenders/{tender_id}/complaints/{complaint_id}"
    return url_pattern.format(host=PUBLIC_API_HOST, version=API_VERSION, **complaint_params)


def prozorro_portal_tender_path(tender_pretty_id):
    return "/tender/{tender_pretty_id}".format(tender_pretty_id=tender_pretty_id)


def prozorro_api_url(path):
    return "{host}/api/{version}{path}".format(host=PUBLIC_API_HOST, version=API_VERSION, path=path)


def prozorro_portal_url(path):
    return "{host}{path}".format(host=PORTAL_HOST, path=path)
