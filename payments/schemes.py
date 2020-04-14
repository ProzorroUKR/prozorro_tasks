import jmespath

from app.utils import datetime_isoformat, datetime_replace_microseconds, datetime_astimezone
from payments.data import complaint_status_description, complaint_reject_description, complaint_funds_description

payment_scheme = {
    "description": {
        "title": "Призначення платежу",
        "path": "payment.description",
        "default": "",
    },
    "amount": {
        "title": "Сума платежу",
        "path": "payment.amount",
        "default": "",
    },
    "currency": {
        "title": "Валюта платежу",
        "path": "payment.currency",
        "default": "",
    },
    "date_oper": {
        "title": "Дата операції",
        "path": "payment.date_oper",
        "default": "",
    },
    "type": {
        "title": "Тип операції",
        "path": "payment.type",
        "default": "",
    },
    "account": {
        "title": "Номер рахунку",
        "path": "payment.account",
        "default": "",
    },
    "okpo": {
        "title": "ОКПО рахунку",
        "path": "payment.okpo",
        "default": "",
    },
    "mfo": {
        "title": "МФО рахунку",
        "path": "payment.mfo",
        "default": "",
    },
    "name": {
        "title": "Назва рахунку",
        "path": "payment.name",
        "default": "",
    },
}
resolution_scheme = {
    "type": {
        "title": "Рішення по скарзі",
        "path": "resolution.type",
        "method": complaint_status_description,
        "default": "",
    },
    "date": {
        "title": "Дата рішення",
        "path": "resolution.date",
        "default": "",
    },
    "reason": {
        "title": "Причина",
        "path": "resolution.reason",
        "method": complaint_reject_description,
        "default": "",
    },
    "funds": {
        "title": "Висновок",
        "path": "resolution.funds",
        "method": complaint_funds_description,
        "default": "",
    },
}
extra_scheme = {
    "user": {
        "title": "Ініціатор",
        "path": "user",
        "default": "",
    },
    "created": {
        "title": "Дата отримання",
        "path": "createdAt",
        "method": lambda x: datetime_isoformat(datetime_replace_microseconds(datetime_astimezone(x))),
        "default": "",
    },
}
full_scheme = {
    "id": {
        "title": "ID",
        "path": "_id",
        "default": "",
    },
    "payment": {
        "title": "Операція",
        "scheme": payment_scheme,
        "default": "",
    },
    "extra": {
        "title": "Додатково",
        "scheme": extra_scheme,
        "default": "",
    },
    "resolution": {
        "title": "Рішення",
        "scheme": resolution_scheme,
        "default": "",
    },
}


def get_scheme_value(data, scheme_info):
    if "scheme" in scheme_info:
        value = {}
        for scheme_nested_field, scheme_nested_info in scheme_info["scheme"].items():
            value.update({scheme_nested_field: get_scheme_item(data, scheme_nested_info)})
        return value
    value = jmespath.search(scheme_info["path"], data) or scheme_info.get("default")
    if "method" in scheme_info:
        value = scheme_info["method"](value)
    return value


def get_scheme_title(data, scheme_info):
    if "title" in scheme_info:
        return scheme_info["title"]
    return None


def get_scheme_item(data, scheme_info):
    value = get_scheme_value(data, scheme_info)
    title = get_scheme_title(data, scheme_info)
    item = dict(value=value)
    if title:
        item.update(dict(title=title))
    return item


def get_scheme_data(data, scheme):
    data_formatted = {}
    for scheme_field, scheme_info in scheme.items():
        data_formatted.update({scheme_field: get_scheme_item(data, scheme_info)})
    return data_formatted
