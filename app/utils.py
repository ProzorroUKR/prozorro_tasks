from ipaddress import ip_network

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
