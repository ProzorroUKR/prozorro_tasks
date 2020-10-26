import jmespath

from payments.data import (
    complaint_status_description,
    complaint_reject_description,
    complaint_funds_description,
    date_representation,
    processing_message_list_description,
    processing_message_failed_list_description,
    processing_date,
    complainant_id,
    complainant_name,
    complainant_telephone,
    value_amount_representation,
)

PAYMENT_DESCRIPTION_SCHEME_ITEM = {
    "type": "object",
    "title": "Призначення платежу",
    "path": "payment.description",
    "default": "",
}

PAYMENT_AMOUNT_SCHEME_ITEM = {
    "type": "object",
    "title": "Сума платежу",
    "path": "payment.amount",
    "default": "",
}

PAYMENT_CURRENCY_SCHEME_ITEM = {
    "type": "object",
    "title": "Валюта платежу",
    "path": "payment.currency",
    "default": "",
}

PAYMENT_DATE_OPER_SCHEME_ITEM = {
    "type": "object",
    "title": "Дата операції",
    "path": "payment.date_oper",
    "default": "",
}

PAYMENT_TYPE_SCHEME_ITEM = {
    "type": "object",
    "title": "Тип операції",
    "path": "payment.type",
    "default": "",
}

PAYMENT_SOURCE_SCHEME_ITEM = {
    "type": "object",
    "title": "Метод операції",
    "path": "payment.source",
    "default": "",
}

PAYMENT_ACCOUNT_SCHEME_ITEM = {
    "type": "object",
    "title": "Номер рахунку",
    "path": "payment.account",
    "default": "",
}

PAYMENT_OKPO_SCHEME_ITEM = {
    "type": "object",
    "title": "ОКПО рахунку",
    "path": "payment.okpo",
    "default": "",
}

PAYMENT_MFO_SCHEME_ITEM = {
    "type": "object",
    "title": "МФО рахунку",
    "path": "payment.mfo",
    "default": "",
}

PAYMENT_NAME_SCHEME_ITEM = {
    "type": "object",
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
    "source": PAYMENT_SOURCE_SCHEME_ITEM,
    "account": PAYMENT_ACCOUNT_SCHEME_ITEM,
    "okpo": PAYMENT_OKPO_SCHEME_ITEM,
    "mfo": PAYMENT_MFO_SCHEME_ITEM,
    "name": PAYMENT_NAME_SCHEME_ITEM,
}

RESOLUTION_TYPE_SCHEME_ITEM = {
    "type": "object",
    "title": "Рішення по скарзі",
    "path": "resolution.type",
    "method": complaint_status_description,
    "default": "",
}

RESOLUTION_DATE_SCHEME_ITEM = {
    "type": "object",
    "title": "Дата рішення",
    "path": "resolution.date",
    "method": date_representation,
    "default": "",
}

RESOLUTION_REASON_SCHEME_ITEM = {
    "type": "object",
    "title": "Причина рішення",
    "path": "resolution.reason",
    "method": complaint_reject_description,
}

RESOLUTION_FUNDS_SCHEME_ITEM = {
    "type": "object",
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
    "type": "object",
    "title": "Ініціатор",
    "path": "user",
    "default": "",
}

EXTRA_CREATED_SCHEME_ITEM = {
    "type": "object",
    "title": "Дата отримання",
    "path": "createdAt",
    "method": date_representation,
    "default": "",
}

EXTRA_PROCESSING_STATUS_SCHEME_ITEM = {
    "type": "object",
    "title": "Статус обробки",
    "path": "messages",
    "method": processing_message_list_description,
    "default": "",
}

EXTRA_PROCESSING_FAILED_STATUS_SCHEME_ITEM = {
    "type": "object",
    "title": "Опис обробки платежу",
    "path": "messages",
    "method": processing_message_failed_list_description,
}

EXTRA_PROCESSING_DATE_SCHEME_ITEM = {
    "type": "object",
    "title": "Дата завершення обробки платежу",
    "path": ".",
    "method": processing_date,
}

EXTRA_COMPLAINANT_ID = {
    "type": "object",
    "title": "Код ЄДРПОУ скаржника",
    "path": ".",
    "method": complainant_id,
}

EXTRA_COMPLAINANT_NAME = {
    "type": "object",
    "title": "Найменування скаржника",
    "path": ".",
    "method": complainant_name,
}

EXTRA_COMPLAINANT_TELEPHONE = {
    "type": "object",
    "title": "Контакти",
    "path": ".",
    "method": complainant_telephone,
}

EXTRA_SCHEME = {
    "user": EXTRA_USER_SCHEME_ITEM,
    "created": EXTRA_CREATED_SCHEME_ITEM,
    "processing_status": EXTRA_PROCESSING_STATUS_SCHEME_ITEM,
    "processing_failed_status": EXTRA_PROCESSING_FAILED_STATUS_SCHEME_ITEM,
    "processing_date": EXTRA_PROCESSING_DATE_SCHEME_ITEM,
    "complainant_id": EXTRA_COMPLAINANT_ID,
    "complainant_name": EXTRA_COMPLAINANT_NAME,
    "complainant_telephone": EXTRA_COMPLAINANT_TELEPHONE,
}

ROOT_ID_SCHEME_ITEM = {
    "type": "object",
    "title": "ID",
    "path": "_id",
    "default": "",
}

ROOT_PAYMENT_SCHEME_ITEM = {
    "type": "object",
    "title": "Операція",
    "scheme": PAYMENT_SCHEME,
    "default": "",
}

ROOT_EXTRA_SCHEME_ITEM = {
    "type": "object",
    "title": "Додатково",
    "scheme": EXTRA_SCHEME,
    "default": "",
}

ROOT_RESOLUTION_SCHEME_ITEM = {
    "type": "object",
    "title": "Рішення",
    "scheme": RESOLUTION_SCHEME,
    "default": "",
}

ROOT_MESSAGES_SCHEME_ITEM = {
    "type": "value",
    "path": "messages",
}

ROOT_PARAMS_SCHEME_ITEM = {
    "type": "value",
    "path": "params",
}

ROOT_SCHEME = {
    "id": ROOT_ID_SCHEME_ITEM,
    "payment": ROOT_PAYMENT_SCHEME_ITEM,
    "extra": ROOT_EXTRA_SCHEME_ITEM,
    "resolution": ROOT_RESOLUTION_SCHEME_ITEM,
    "messages": ROOT_MESSAGES_SCHEME_ITEM,
    "params": ROOT_PARAMS_SCHEME_ITEM,
}

REPORT_AMOUNT_SCHEME_ITEM = {
    "type": "object",
    "title": "Сума, UAH",
    "path": "payment",
    "method": value_amount_representation,
    "default": "",
}

REPORT_SCHEME = {
    "payment_description": PAYMENT_DESCRIPTION_SCHEME_ITEM,
    "payment_amount": REPORT_AMOUNT_SCHEME_ITEM,
    "payment_date_oper": PAYMENT_DATE_OPER_SCHEME_ITEM,
    "payment_account": PAYMENT_ACCOUNT_SCHEME_ITEM,
    "payment_okpo": PAYMENT_OKPO_SCHEME_ITEM,
    "payment_name": PAYMENT_NAME_SCHEME_ITEM,
    "complainant_id": EXTRA_COMPLAINANT_ID,
    "complainant_name": EXTRA_COMPLAINANT_NAME,
    "complainant_telephone": EXTRA_COMPLAINANT_TELEPHONE,
    "processing_date": EXTRA_PROCESSING_DATE_SCHEME_ITEM,
    "processing_status": EXTRA_PROCESSING_STATUS_SCHEME_ITEM,
    "processing_failed_status": EXTRA_PROCESSING_FAILED_STATUS_SCHEME_ITEM,
    "resolution_funds": RESOLUTION_FUNDS_SCHEME_ITEM,
}


def get_scheme_value(data, scheme_info):
    if "scheme" in scheme_info:
        return get_scheme_data(data, scheme_info["scheme"])
    if scheme_info["path"] == ".":
        value = data
    else:
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
        scheme_type = scheme_info.get("type")
        if scheme_type == "object":
            item = get_scheme_item(data, scheme_info)
            if item is not None:
                data_formatted.update({scheme_field: item})
        elif scheme_type == "value":
            value = get_scheme_value(data, scheme_info)
            if value is not None:
                data_formatted.update({scheme_field: value})
    return data_formatted
