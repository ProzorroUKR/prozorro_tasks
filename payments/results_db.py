import pymongo
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from pymongo import DESCENDING
from pytz import UTC

from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure, DuplicateKeyError

from environment_settings import TIMEZONE
from payments.message_ids import PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)


DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10


def init_db_indexes():
    drop_db_indexes()
    indexes = [
        dict(keys="createdAt", name="created_at"),
        dict(keys=[('payment.description', pymongo.TEXT)], name="payment_description_text")
    ]
    for kwargs in indexes:
        init_db_index(**kwargs)


def drop_db_indexes():
    try:
        collection = get_mongodb_collection()
        collection.drop_indexes()
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR"})
    return "success"


def init_db_index(**kwargs):
    try:
        collection = get_mongodb_collection()
        collection.create_index(**kwargs)
    except OperationFailure as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        return "exists"
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR"})
    return "success"


def get_payment_count(**kwargs):
    collection = get_mongodb_collection()
    find_filter = get_payment_filters(**kwargs)
    try:
        count = collection.count_documents(find_filter)
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        return count


def get_payment_filters(
    search=None,
    payment_type=None,
    resolution_exists=None,
    resolution_date=None,
    resolution_funds=None,
    message_ids_include=None,
    message_ids_date=None,
    message_ids_exclude=None,
    **kwargs
):
    find_filter = dict()
    if search is not None:
        find_filter.update({"$text": {"$search": search}})
    if payment_type is not None:
        find_filter.update({"payment.type": payment_type})
    if resolution_exists is not None:
        find_filter.update({"resolution": {"$exists": resolution_exists}})
    if resolution_funds is not None:
        find_filter.update({"resolution.funds": resolution_funds})
    if resolution_date is not None:
        find_filter.update({"resolution.date": {
            "$gte": resolution_date.isoformat(),
            "$lt": (resolution_date + timedelta(days=1)).isoformat()
        }})
    if message_ids_include is not None:
        find_filter.update({"messages.message_id": {"$in": message_ids_include}})
    if message_ids_include is not None and message_ids_date is not None:
        message_ids_date = UTC.normalize(TIMEZONE.localize(message_ids_date))
        print(message_ids_date)
        find_filter_part = {"messages" : {"$elemMatch": {
            "message_id": {"$in": message_ids_include},
            "createdAt": {
                "$gte": message_ids_date.astimezone(UTC),
                "$lt": (message_ids_date + timedelta(days=1)).astimezone(UTC)
            }
        }}}
        find_filter.update(find_filter_part)
        print(find_filter_part)
    if message_ids_exclude is not None:
        find_filter.update({"messages.message_id": {"$not": {"$in": message_ids_exclude}}})
    return find_filter


def get_payment_list(page=DEFAULT_PAGE, limit=DEFAULT_LIMIT, **kwargs):
    skip = page * limit - limit
    collection = get_mongodb_collection()
    find_filter = get_payment_filters(**kwargs)
    try:
        doc = collection.find(find_filter).sort("createdAt", DESCENDING).skip(skip).limit(limit)
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        return doc


def get_payment_item(uid):
    collection = get_mongodb_collection()
    try:
        doc = collection.find_one(
            {"_id": uid}
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        return doc


def push_payment_message(data, message_id, message):
    uid = args_to_uid(sorted(data.values()))
    collection = get_mongodb_collection()
    try:
        doc = collection.update(
            {"_id": uid},
            {'$push': {
                'messages': {
                    "message_id": message_id,
                    "message": message,
                    "createdAt": datetime.utcnow()
                }
            }}
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_PUSH_MESSAGE_MONGODB_EXCEPTION"})
        raise
    else:
        return doc


def save_payment_item(data, user):
    uid = args_to_uid(sorted(data.values()))
    collection = get_mongodb_collection()
    try:
        collection.insert({
            "_id": uid,
            "payment": data,
            "user": user,
            "createdAt": datetime.utcnow(),
        })
    except DuplicateKeyError:
        pass
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_POST_RESULTS_MONGODB_EXCEPTION"})
        raise
    else:
        return uid


def set_payment_params(data, params):
    uid = args_to_uid(sorted(data.values()))
    collection = get_mongodb_collection()
    try:
        collection.update(
            {"_id": uid},
            {'$set': {
                'params': params
            }})
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_SET_PARAMS_MONGODB_EXCEPTION"})
        raise
    else:
        return uid


def get_payment_item_by_params(params):
    collection = get_mongodb_collection()
    try:
        doc = collection.find({
            "params": params
        })
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_BY_PARAMS_MONGODB_EXCEPTION"})
        raise
    else:
        items = list(doc)
        if len(items) == 1:
            return items[0]
        elif len(items) > 1:
            return get_payment_item_by_params_and_message_id(
                params, PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS
            )


def get_payment_item_by_params_and_message_id(params, message_id):
    collection = get_mongodb_collection()
    try:
        doc = collection.find_one({
            "params": params,
            "messages.message_id": message_id
        })
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_BY_PARAM_AND_MESSAGE_ID_MONGODB_EXCEPTION"})
        raise
    else:
        return doc


def set_payment_resolution(data, resolution):
    uid = args_to_uid(sorted(data.values()))
    collection = get_mongodb_collection()
    try:
        collection.update(
            {"_id": uid},
            {'$set': {
                'resolution': resolution
            }})
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_SET_RESOLUTION_MONGODB_EXCEPTION"})
        raise
    else:
        return uid
