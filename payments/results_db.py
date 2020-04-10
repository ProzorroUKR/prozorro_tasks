import pymongo
from datetime import datetime
from celery.utils.log import get_task_logger
from pymongo import DESCENDING

from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure, DuplicateKeyError

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)


DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10


def init_db_indexes():
    indexes = [
        dict(keys="createdAt"),
        dict(keys=[('payment.description', pymongo.TEXT)])
    ]
    for kwargs in indexes:
        init_db_index(**kwargs)


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


def get_payment_count(search=None, payment_type=None, **kwargs):
    collection = get_mongodb_collection()
    find_filter = dict()
    if payment_type:
        find_filter.update({"payment.type": payment_type})
    if search:
        find_filter.update({"$text": {"$search": search}})
    try:
        count = collection.count_documents(find_filter)
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        return count


def get_payment_list(search=None, payment_type=None, page=DEFAULT_PAGE, limit=DEFAULT_LIMIT, **kwargs):
    skip = page * limit - limit
    collection = get_mongodb_collection()
    find_filter = dict()
    if search:
        find_filter.update({"$text": {"$search": search}})
    if payment_type:
        find_filter.update({"payment.type": payment_type})
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
    else:
        return uid
