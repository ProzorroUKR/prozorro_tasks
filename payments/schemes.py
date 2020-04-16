import jmespath

from payments.data import (
    complaint_status_description,
    complaint_reject_description,
    complaint_funds_description,
    date_representation,
    processing_message_list_description,
)

PAYMENT_DESCRIPTION_SCHEME_ITEM = {
    "title": "Призначення платежу",
    "path": "payment.description",
    "default": "",
}

PAYMENT_AMOUNT_SCHEME_ITEM = {
    "title": "Сума платежу",
    "path": "payment.amount",
    "default": "",
}

PAYMENT_CURRENCY_SCHEME_ITEM = {
    "title": "Валюта платежу",
    "path": "payment.currency",
    "default": "",
}

PAYMENT_DATE_OPER_SCHEME_ITEM = {
    "title": "Дата операції",
    "path": "payment.date_oper",
    "default": "",
}

PAYMENT_TYPE_SCHEME_ITEM = {
    "title": "Тип операції",
    "path": "payment.type",
    "default": "",
}

PAYMENT_ACCOUNT_SCHEME_ITEM = {
    "title": "Номер рахунку",
    "path": "payment.account",
    "default": "",
}

PAYMENT_OKPO_SCHEME_ITEM = {
    "title": "ОКПО рахунку",
    "path": "payment.okpo",
    "default": "",
}

PAYMENT_MFO_SCHEME_ITEM = {
    "title": "МФО рахунку",
    "path": "payment.mfo",
    "default": "",
}

PAYMENT_NAME_SCHEME_ITEM = {
    "title": "Назва рахунку",
    "path": "payment.name",
    "default": "",
}

PAYMENT_SCHEME = {
    "description": PAYMENT_DESCRIPTION_SCHEME_ITEM,
    "amount": PAYMENT_AMOUNT_SCHEME_ITEM,
    "currency": PAYMENT_CURRENCY_SCHEME_ITEM,
    "date_oper": PAYMENT_DATE_OPER_SCHEME_ITEM,
    "type": PAYMENT_TYPE_SCHEME_ITEM,
    "account": PAYMENT_ACCOUNT_SCHEME_ITEM,
    "okpo": PAYMENT_OKPO_SCHEME_ITEM,
    "mfo": PAYMENT_MFO_SCHEME_ITEM,
    "name": PAYMENT_NAME_SCHEME_ITEM,
}

RESOLUTION_TYPE_SCHEME_ITEM = {
    "title": "Рішення по скарзі",
    "path": "resolution.type",
    "method": complaint_status_description,
    "default": "",
}

RESOLUTION_DATE_SCHEME_ITEM = {
    "title": "Дата рішення",
    "path": "resolution.date",
    "method": date_representation,
    "default": "",
}

RESOLUTION_REASON_SCHEME_ITEM = {
    "title": "Причина",
    "path": "resolution.reason",
    "method": complaint_reject_description,
}

RESOLUTION_FUNDS_SCHEME_ITEM = {
    "title": "Висновок",
    "path": "resolution.funds",
    "method": complaint_funds_description,
    "default": "",
}

RESOLUTION_SCHEME = {
    "type": RESOLUTION_TYPE_SCHEME_ITEM,
    "reason": RESOLUTION_REASON_SCHEME_ITEM,
    "date": RESOLUTION_DATE_SCHEME_ITEM,
    "funds": RESOLUTION_FUNDS_SCHEME_ITEM,
}

EXTRA_USER_SCHEME_ITEM = {
    "title": "Ініціатор",
    "path": "user",
    "default": "",
}

EXTRA_CREATED_SCHEME_ITEM = {
    "title": "Дата отримання",
    "path": "createdAt",
    "method": date_representation,
    "default": "",
}

EXTRA_SCHEME = {
    "user": EXTRA_USER_SCHEME_ITEM,
    "created": EXTRA_CREATED_SCHEME_ITEM,
}

ROOT_ID_SCHEME_ITEM = {
    "title": "ID",
    "path": "_id",
    "default": "",
}

ROOT_PAYMENT_SCHEME_ITEM = {
    "title": "Операція",
    "scheme": PAYMENT_SCHEME,
    "default": "",
}

ROOT_EXTRA_SCHEME_ITEM = {
    "title": "Додатково",
    "scheme": EXTRA_SCHEME,
    "default": "",
}

ROOT_PROCESSING_SCHEME_ITEM = {
    "title": "Статус обробки",
    "path": "messages",
    "method": processing_message_list_description,
    "default": "",
}

ROOT_RESOLUTION_SCHEME_ITEM = {
    "title": "Рішення",
    "scheme": RESOLUTION_SCHEME,
    "default": "",
}

ROOT_SCHEME = {
    "id": ROOT_ID_SCHEME_ITEM,
    "payment": ROOT_PAYMENT_SCHEME_ITEM,
    "extra": ROOT_EXTRA_SCHEME_ITEM,
    "resolution": ROOT_RESOLUTION_SCHEME_ITEM,
    "processing": ROOT_PROCESSING_SCHEME_ITEM,
}

REPORT_SCHEME = {
    "payment_description": PAYMENT_DESCRIPTION_SCHEME_ITEM,
    "payment_amount": PAYMENT_AMOUNT_SCHEME_ITEM,
    "payment_currency": PAYMENT_CURRENCY_SCHEME_ITEM,
    "payment_date_oper": PAYMENT_DATE_OPER_SCHEME_ITEM,
    "resolution_type": RESOLUTION_TYPE_SCHEME_ITEM,
    "resolution_date": RESOLUTION_DATE_SCHEME_ITEM,
    "payment_type": PAYMENT_TYPE_SCHEME_ITEM,
    "payment_account": PAYMENT_ACCOUNT_SCHEME_ITEM,
    "payment_okpo": PAYMENT_OKPO_SCHEME_ITEM,
    "payment_mfo": PAYMENT_MFO_SCHEME_ITEM,
    "payment_name": PAYMENT_NAME_SCHEME_ITEM,
    "resolution_reason": RESOLUTION_REASON_SCHEME_ITEM,
    "resolution_funds": RESOLUTION_FUNDS_SCHEME_ITEM,
    "processing": ROOT_PROCESSING_SCHEME_ITEM,
}


def get_scheme_value(data, scheme_info):
    if "scheme" in scheme_info:
        return get_scheme_data(data, scheme_info["scheme"])
    value = jmespath.search(scheme_info["path"], data)
    if "method" in scheme_info:
        value = scheme_info["method"](value)
    value = value or scheme_info.get("default")
    if value is not None:
        return value


def get_scheme_title(data, scheme_info):
    if "title" in scheme_info:
        return scheme_info["title"]
    return None


def get_scheme_item(data, scheme_info):
    value = get_scheme_value(data, scheme_info)
    if value is not None:
        title = get_scheme_title(data, scheme_info)
        item = dict(value=value)
        if title:
            item.update(dict(title=title))
        return item


def get_scheme_data(data, scheme):
    data_formatted = {}
    for scheme_field, scheme_info in scheme.items():
        item = get_scheme_item(data, scheme_info)
        if item is not None:
            data_formatted.update({scheme_field: item})
    return data_formatted
