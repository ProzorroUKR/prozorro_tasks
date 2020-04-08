import typing

from environment_settings import TIMEZONE


def is_dict(item):
    return isinstance(item, typing.Dict)


def localize(dt):
    return dt.astimezone(TIMEZONE)
