import typing

from environment_settings import TIMEZONE, PUBLIC_API_HOST, API_VERSION, PORTAL_HOST


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
    url_pattern = "/tenders/{tender_id}/{item_type}"
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
