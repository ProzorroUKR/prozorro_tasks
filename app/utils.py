from flask import request

from app.settings import APP_AUIP_HEADER


def get_auth_users(config):
    users = {}
    for group in config.sections():
        for username, password in config.items(group):
            groups = get_auth_user_groups(config, username, password)
            users.update({username: dict(password=password, groups=groups)})
    return users


def get_auth_user_groups(config, username, password):
    return [
        group for group in config.sections()
        for u, p in config.items(group)
        if u == username and p == password
    ]


def get_auth_ips(config):
    return {
        ip: dict(username=username, group=group)
        for group in config.sections()
        for username, ips in config.items(group)
        for ip in ips.split(",")
    }


def get_remote_addr(req):
    if APP_AUIP_HEADER:
        return req.headers.get(APP_AUIP_HEADER)
    return request.remote_addr
