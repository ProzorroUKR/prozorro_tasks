from datetime import datetime
from celery.utils.log import get_task_logger
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from environment_settings import MONGODB_URL
import sys
import hashlib

logger = get_task_logger(__name__)
MONGODB_UID_LENGTH = 24


def get_mongodb_collection():
    client = MongoClient(MONGODB_URL)  # TODO handle exceptions
    db = client.erd_bot
    return db.upload_results


# https://docs.mongodb.com/manual/tutorial/expire-data/
if "unittest" not in sys.argv[0]:   # pragma: no cover
    try:
        get_mongodb_collection().create_index(
            "createdAt",
            expireAfterSeconds=30 * 3600  # delete index when you've changed this
        )
    except OperationFailure as e:
        logger.exception(e)


def hash_string_to_uid(input_string):
    h = hashlib.shake_256()
    h.update(input_string.encode("utf-8"))
    return h.hexdigest(int(MONGODB_UID_LENGTH / 2))


def args_to_uid(args):
    args_string = "".join((str(a) for a in args))
    uid = hash_string_to_uid(args_string)
    return uid


def get_upload_results(self, *args):
    uid = args_to_uid(args)
    collection = get_mongodb_collection()
    try:
        doc = collection.find_one(  # TODO set timeouts
            {'_id': uid}
        )
    except Exception as exc:  # TODO except less
        logger.exception(exc)
        raise self.retry()
    else:
        return doc


def save_upload_results(response_json, *args):
    uid = args_to_uid(args)
    collection = get_mongodb_collection()
    try:
        collection.insert({
            '_id': uid,
            'file_data': response_json,
            'createdAt': datetime.utcnow(),
        })
    except Exception as exc:
        logger.exception(exc)
    else:
        return uid


def set_upload_results_attached(*args):
    uid = args_to_uid(args)
    collection = get_mongodb_collection()
    try:
        collection.update_one(
            {'_id': uid},
            {'attached': True}
        )
    except Exception as exc:
        logger.exception(exc)
    else:
        return uid
