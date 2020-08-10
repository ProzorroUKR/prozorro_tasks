import pymongo
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from pymongo import DESCENDING
from pytz import UTC

from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure, DuplicateKeyError

from environment_settings import TIMEZONE
from app.logging import log_exc
from payments.utils import filter_payment_data

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)

get_mongodb_status_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_status"
)

UID_KEYS_1 = [
    "description",
    "amount",
    "currency",
    "date_oper",
    "type",
    "account",
    "okpo",
    "mfo",
    "name",
]

UID_KEYS_2 = UID_KEYS_1 + [
    "source",
]

UID_KEYS_3 = UID_KEYS_2 + [
    "odb_ref",
]


def init_indexes():
    collection = get_mongodb_collection()
    drop_indexes(collection)
    indexes = [
        dict(keys="createdAt", name="created_at"),
        dict(keys=[("payment.description", pymongo.TEXT)], name="payment_description_text"),
    ]
    for kwargs in indexes:
        try:
            init_index(collection, **kwargs)
        except OperationFailure:
            # Index already exists
            pass

    status_collection = get_mongodb_status_collection()
    try:
        init_index(status_collection, keys="createdAt", expireAfterSeconds=24 * 3600 * 30)
    except OperationFailure:
        # Index already exists
        pass


@log_exc(logger, PyMongoError, "MONGODB_INDEX_DROP_UNEXPECTED_ERROR")
def drop_indexes(collection):
    collection.drop_indexes()


@log_exc(logger, PyMongoError, "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR")
@log_exc(logger, OperationFailure, "MONGODB_INDEX_CREATION_ERROR")
def init_index(collection, **kwargs):
    collection.create_index(**kwargs)


def data_to_uid(data, keys=None):
    return args_to_uid(sorted([
        str(value) if not isinstance(value, dict) else data_to_uid(value)
        for key, value in data.items()
        if keys is None or key in keys
    ]))


def payment_find_query(data):
    return {
        "$or": [
            {"_id": data_to_uid(data, keys=UID_KEYS_3)},
            {"_id": data_to_uid(data, keys=UID_KEYS_2)},
            {"_id": data_to_uid(data, keys=UID_KEYS_1)},
        ]
    }


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_COUNT_MONGODB_EXCEPTION")
def get_payment_count(filters, **kwargs):
    collection = get_mongodb_collection()
    return collection.count_documents(filters)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION")
def get_payment_list(filters=None, page=None, limit=None, **kwargs):
    collection = get_mongodb_collection()
    cursor = collection.find(filters).sort("createdAt", DESCENDING)
    if page and limit:
        skip = (page - 1) * limit
        if skip >= 0:
            cursor = cursor.skip(skip)
    if limit:
        cursor = cursor.limit(limit)
    return cursor


@log_exc(logger, PyMongoError, "PAYMENTS_PUSH_MESSAGE_MONGODB_EXCEPTION")
def push_payment_message(data, message_id, message):
    collection = get_mongodb_collection()
    query = payment_find_query(data)
    update = {
        "$push": {
            "messages": {
                "message_id": message_id,
                "message": message,
                "createdAt": datetime.utcnow()
            }
        }
    }
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_COUNT_MONGODB_EXCEPTION")
def find_payment_item(data, **kwargs):
    collection = get_mongodb_collection()
    query = payment_find_query(data)
    return collection.find_one(query)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_ITEM_MONGODB_EXCEPTION")
def get_payment_item(uid):
    collection = get_mongodb_collection()
    query = {"_id": uid}
    return collection.find_one(query)


@log_exc(logger, PyMongoError, "PAYMENTS_SAVE_RESULTS_MONGODB_EXCEPTION")
def save_payment_item(data, user):
    status = data.get("status")
    if status and status != "success":
        return
    collection = get_mongodb_collection()
    uid = data_to_uid(data, keys=UID_KEYS_3)
    document = {
        "_id": uid,
        "payment": filter_payment_data(data),
        "user": user,
        "createdAt": datetime.utcnow(),
    }
    try:
        return collection.insert_one(document)
    except DuplicateKeyError:
        pass


@log_exc(logger, PyMongoError, "PAYMENTS_UPDATE_RESULTS_MONGODB_EXCEPTION")
def update_payment_item(uid, data):
    collection = get_mongodb_collection()
    query = {
        "_id": uid,
    }
    update = {
        "$set": {
            "payment": filter_payment_data(data),
            "updatedAt": datetime.utcnow(),
        }
    }
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_SET_PARAMS_MONGODB_EXCEPTION")
def set_payment_params(data, params):
    collection = get_mongodb_collection()
    query = payment_find_query(data)
    update = {"$set": {"params": params}}
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_SET_RESOLUTION_MONGODB_EXCEPTION")
def set_payment_resolution(data, resolution):
    collection = get_mongodb_collection()
    query = payment_find_query(data)
    update = {"$set": {"resolution": resolution}}
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_BY_PARAMS_MONGODB_EXCEPTION")
def get_payment_item_by_params(params, message_ids=None):
    collection = get_mongodb_collection()
    filters = [{"params": params}]
    if message_ids:
        filters.append({"messages.message_id": {"$in": message_ids}})
    return collection.find_one(combined_filters_and(filters))


def get_payment_search_filters(
    search=None,
    payment_type=None,
    payment_source=None,
    payment_date_from=None,
    payment_date_to=None,
    **kwargs
):
    filters = []
    if search is not None:
        filters.append({"$text": {"$search": search}})
    if payment_type is not None:
        filters.append({"payment.type": payment_type})
    if payment_source is not None:
        filters.append({"payment.source": payment_source})
    if payment_date_from is not None and payment_date_to is not None:
        filters.append({
            "$expr": {
                "$and": [
                    {"$gte": [date_from_str_filter("$payment.date_oper"), payment_date_from]},
                    {"$lt": [date_from_str_filter("$payment.date_oper"), payment_date_to]}
                ]
            }
        })
    return combined_filters_and(filters) if filters else {}


def get_payment_report_success_filters(
    resolution_exists=None,
    resolution_date_to=None,
    resolution_date_from=None,
    resolution_funds=None,
    **kwargs
):
    filters = []
    if resolution_exists is not None:
        filters.append({"resolution": {"$exists": resolution_exists}})
    if resolution_funds is not None:
        filters.append({"resolution.funds": resolution_funds})
    if resolution_date_from is not None and resolution_date_to is not None:
        filters.append({
            "resolution.date": {
                "$gte": resolution_date_from.isoformat(),
                "$lt": (resolution_date_to + timedelta(days=1)).isoformat()
            }
        })
    return combined_filters_and(filters) if filters else {}


def get_payment_report_failed_filters(
    message_ids_include=None,
    message_ids_date_from=None,
    message_ids_date_to=None,
    message_ids_exclude=None,
    **kwargs
):
    filters = []
    if message_ids_include is not None:
        filters.append({"messages.message_id": {"$in": message_ids_include}})
    messages_match_filter = {}
    if message_ids_include is not None:
        messages_match_filter.update({"message_id": {"$in": message_ids_include}})
    if message_ids_date_from is not None and message_ids_date_to is not None:
        message_ids_date_from = UTC.normalize(TIMEZONE.localize(message_ids_date_from))
        message_ids_date_to = UTC.normalize(TIMEZONE.localize(message_ids_date_to))
        messages_match_filter.update({
            "createdAt": {
                "$gte": message_ids_date_from,
                "$lt": message_ids_date_to + timedelta(days=1)
            }
        })
    filters.append({"messages": {"$elemMatch": messages_match_filter}})
    if message_ids_exclude is not None:
        filters.append({"messages.message_id": {"$not": {"$in": message_ids_exclude}}})
    return combined_filters_and(filters) if filters else {}


def combined_filters_and(filters):
    return {"$and": filters}


def combined_filters_or(filters):
    return {"$or": filters}


def date_from_str_filter(field):
    return {
        "$dateFromString": {
            "dateString": field,
            "format": "%d.%m.%Y %H:%M:%S",
            "onError": None
        }
    }


@log_exc(logger, PyMongoError, "PAYMENTS_STATUS_LIST_MONGODB_EXCEPTION")
def get_statuses_list(limit=None):
    collection = get_mongodb_status_collection()
    cursor = collection.find().sort("createdAt", DESCENDING)
    if limit:
        cursor = cursor.limit(limit)
    return cursor


@log_exc(logger, PyMongoError, "PAYMENTS_STATUS_SAVE_MONGODB_EXCEPTION")
def save_status(data):
    collection = get_mongodb_status_collection()
    try:
        insert_data = {
            "_id": data_to_uid(data),
            "data": data.copy(),
            "createdAt": datetime.utcnow(),
        }
        collection.insert(insert_data)
        return insert_data
    except DuplicateKeyError:
        pass
