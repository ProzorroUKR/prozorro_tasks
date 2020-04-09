from datetime import datetime
from celery.utils.log import get_task_logger
from pymongo import DESCENDING

from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)


def init_db_index():
    # https://docs.mongodb.com/manual/tutorial/expire-data/
    try:
        get_mongodb_collection().create_index(
            "createdAt",
            expireAfterSeconds=30 * 3600  # delete index when you"ve changed this
        )
    except OperationFailure as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        return "exists"
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR"})
    return "success"


def get_payment_count():
    collection = get_mongodb_collection()
    try:
        doc = collection.find().sort("createdAt", DESCENDING).count()
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        return doc


def get_payment_list(page, limit):
    skip = page * limit - limit
    collection = get_mongodb_collection()
    try:
        doc = collection.find().sort("createdAt", DESCENDING).skip(skip).limit(limit)
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


def retry_payment_item(uid):
    collection = get_mongodb_collection()
    try:
        doc = collection.find_one(
            {"_id": uid}
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION"})
    else:
        from payments.tasks import process_payment_data
        if doc and doc.get("payment", {}):
            payment = doc.get("payment", {})
            process_payment_data.apply_async(kwargs=dict(
                payment_data=dict(
                    description=payment.get("description"),
                    amount=payment.get("amount"),
                    currency=payment.get("currency"),
                )
            ))
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
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "PAYMENTS_POST_RESULTS_MONGODB_EXCEPTION"})
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
