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

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)


def init_indexes():
    drop_indexes()
    indexes = [
        dict(keys="createdAt", name="created_at"),
        dict(keys=[('payment.description', pymongo.TEXT)], name="payment_description_text")
    ]
    for kwargs in indexes:
        try:
            init_index(**kwargs)
        except OperationFailure:
            # Index already exists
            pass


@log_exc(logger, PyMongoError, "MONGODB_INDEX_DROP_UNEXPECTED_ERROR")
def drop_indexes():
    collection = get_mongodb_collection()
    collection.drop_indexes()


@log_exc(logger, PyMongoError, "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR")
@log_exc(logger, OperationFailure, "MONGODB_INDEX_CREATION_ERROR")
def init_index(**kwargs):
    collection = get_mongodb_collection()
    collection.create_index(**kwargs)


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


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_ITEM_MONGODB_EXCEPTION")
def get_payment_item(uid):
    collection = get_mongodb_collection()
    return collection.find_one({"_id": uid})


@log_exc(logger, PyMongoError, "PAYMENTS_PUSH_MESSAGE_MONGODB_EXCEPTION")
def push_payment_message(data, message_id, message):
    collection = get_mongodb_collection()
    return collection.update(
        {"_id": data_to_uid(data)},
        {'$push': {
            'messages': {
                "message_id": message_id,
                "message": message,
                "createdAt": datetime.utcnow()
            }
        }}
    )


@log_exc(logger, PyMongoError, "PAYMENTS_POST_RESULTS_MONGODB_EXCEPTION")
def save_payment_item(data, user):
    collection = get_mongodb_collection()
    try:
        return collection.insert({
            "_id": data_to_uid(data),
            "payment": data,
            "user": user,
            "createdAt": datetime.utcnow(),
        })
    except DuplicateKeyError:
        pass


@log_exc(logger, PyMongoError, "PAYMENTS_SET_PARAMS_MONGODB_EXCEPTION")
def set_payment_params(data, params):
    collection = get_mongodb_collection()
    return collection.update(
        {"_id": data_to_uid(data)},
        {'$set': {'params': params}}
    )


@log_exc(logger, PyMongoError, "PAYMENTS_SET_RESOLUTION_MONGODB_EXCEPTION")
def set_payment_resolution(data, resolution):
    collection = get_mongodb_collection()
    return collection.update(
        {"_id": data_to_uid(data)},
        {'$set': {'resolution': resolution}}
    )


@log_exc(logger, PyMongoError, "PAYMENTS_GET_BY_PARAMS_MONGODB_EXCEPTION")
def get_payment_item_by_params(params, message_ids=None):
    collection = get_mongodb_collection()
    filters = [{"params": params}]
    if message_ids:
        filters.append({"messages.message_id": {"$in": message_ids}})
    return collection.find_one(get_combined_filters_and(filters))


def data_to_uid(data):
    return args_to_uid(sorted(data.values()))


def get_payment_search_filters(
    search=None,
    payment_type=None,
    **kwargs
):
    filters = []
    if search is not None:
        filters.append({"$text": {"$search": search}})
    if payment_type is not None:
        filters.append({"payment.type": payment_type})
    return get_combined_filters_and(filters) if filters else {}


def get_payment_report_filters(
    resolution_exists=None,
    resolution_date=None,
    resolution_funds=None,
    message_ids_include=None,
    message_ids_date=None,
    message_ids_exclude=None,
    **kwargs
):
    filters = []
    if resolution_exists is not None:
        filters.append({"resolution": {"$exists": resolution_exists}})
    if resolution_funds is not None:
        filters.append({"resolution.funds": resolution_funds})
    if resolution_date is not None:
        filters.append({"resolution.date": {
            "$gte": resolution_date.isoformat(),
            "$lt": (resolution_date + timedelta(days=1)).isoformat()
        }})
    if message_ids_include is not None:
        filters.append({"messages.message_id": {"$in": message_ids_include}})
    if message_ids_include is not None or message_ids_date is not None:
        messages_match_filter = {}
        if message_ids_include is not None:
            messages_match_filter.update({"message_id": {"$in": message_ids_include}})
        if message_ids_date is not None:
            message_ids_date = UTC.normalize(TIMEZONE.localize(message_ids_date))
            messages_match_filter.update({"createdAt": {
                "$gte": message_ids_date,
                "$lt": (message_ids_date + timedelta(days=1))
            }})
        filters.append({"messages" : {"$elemMatch": messages_match_filter}})
    if message_ids_exclude is not None:
        filters.append({"messages.message_id": {"$not": {"$in": message_ids_exclude}}})
    return get_combined_filters_and(filters) if filters else {}


def get_combined_filters_and(filters):
    return {"$and": filters}


def get_combined_filters_or(filters):
    return {"$or": filters}
