from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS, PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
)


PAYMENTS_INFO_MESSAGE_ID_LIST = [
    PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS,
]

PAYMENTS_SUCCESS_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
]

PAYMENTS_WARNING_MESSAGE_ID_LIST = [
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
]

PAYMENTS_DANGER_MESSAGE_ID_LIST = [
    PAYMENTS_INVALID_PATTERN,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_ITEM_NOT_FOUND,
    PAYMENTS_COMPLAINT_NOT_FOUND,
]

PAYMENTS_ERROR_MESSAGE_ID_LIST = [
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_HEAD_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
]

PAYMENTS_MESSAGE_IDS = {
    'success': PAYMENTS_SUCCESS_MESSAGE_ID_LIST,
    'warning': PAYMENTS_WARNING_MESSAGE_ID_LIST,
    'danger': PAYMENTS_DANGER_MESSAGE_ID_LIST,
    'error': PAYMENTS_ERROR_MESSAGE_ID_LIST,
}

def payment_primary_message(payment):
    primary_list = []
    primary_list.extend(PAYMENTS_INFO_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_SUCCESS_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_WARNING_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_DANGER_MESSAGE_ID_LIST)
    primary_list.extend(PAYMENTS_ERROR_MESSAGE_ID_LIST)
    for primary in primary_list:
        for message in payment.get("messages", []):
            if message.get("message_id") == primary:
                return message


def payment_message_status(message):
    if message is None:
        return None
    message_id = message.get("message_id")
    if message_id in PAYMENTS_INFO_MESSAGE_ID_LIST:
        return "info"
    if message_id in PAYMENTS_SUCCESS_MESSAGE_ID_LIST:
        return "success"
    elif message_id in PAYMENTS_WARNING_MESSAGE_ID_LIST:
        return "warning"
    elif message_id in PAYMENTS_ERROR_MESSAGE_ID_LIST:
        return "warning"
    elif message_id in PAYMENTS_DANGER_MESSAGE_ID_LIST:
        return "danger"
    return None


def complaint_status_description(status):
    status_descriptions = dict(
        mistaken="Скасовано",
        resolved="Рішення виконано замовником",
        invalid="Залишено без розгляду",
        satisfied="Задоволено",
        declined="Відхилено",
        accepted="Прийнято до розгляду",
        stopped="Розгляд припинено",
    )
    return status_descriptions.get(status, status)


def complaint_reject_description(reason):
    status_descriptions = {
        "lawNonCompliance": "Скарга не відповідає вимогам частин 2-5 "
                            "та 9 статті 18 Закону про публічні закупівлі",
        "alreadyExists": "Суб’єкт оскарження подає скаргу щодо того самого "
                         "порушення та з тих самих підстав, що вже були предметом "
                         "розгляду органу оскарження і щодо яких органом "
                         "оскарження було прийнято відповідне рішення",
        "buyerViolationsCorrected": "Замовником відповідно до Закону про "
                                    "публічні закупівлі усунено порушення",
        "tenderCancelled": "До дня подання скарги замовником прийнято рішення "
                           "про відміну тендеру чи визнання його таким, "
                           "що не відбувся, крім випадку оскарження "
                           "будь-якого з цих рішень",
        "cancelledByComplainant": "Скарга скасована суб'єктом оскарження",
        "complaintPeriodEnded": "Період оскарження закінчився",
        "incorrectPayment": "Отримана сума оплати не співпадає з розрахованою для даної скарги",
    }
    return status_descriptions.get(reason, reason)


def complaint_funds_description(funds):
    funds_descriptions = {
        "state": "Перерахунок до держбюджету",
        "complainant": "Повернення коштів скаржнику"
    }
    return funds_descriptions.get(funds, funds)
