from datetime import datetime
from celery_worker.celery import app
from celery.utils.log import get_task_logger
from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from celery.signals import celeryd_init
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure
import sys

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="nazk_bot_upload_results"
)


@app.task(bind=True)
def init_db_index(self):
    # https://docs.mongodb.com/manual/tutorial/expire-data/
    try:
        get_mongodb_collection().create_index(
            "createdAt",
            expireAfterSeconds=30 * 3600  # delete index when you've changed this
        )
    except OperationFailure as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        return "exists"
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR"})
        raise self.retry()
    return "success"


if "test" not in sys.argv[0]:  # pragma: no cover

    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        init_db_index.delay()


def get_upload_results(self, *args):
    uid = args_to_uid(args)
    collection = get_mongodb_collection()
    try:
        doc = collection.find_one(
            {'_id': uid}
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_GET_RESULTS_MONGODB_EXCEPTION"})
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
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_POST_RESULTS_MONGODB_EXCEPTION"})
    else:
        return uid


def set_upload_results_attached(*args):
    uid = args_to_uid(args)
    collection = get_mongodb_collection()
    try:
        collection.update_one(
            {'_id': uid},
            {"$set": {'attached': True}}
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "EDR_UPDATE_RESULTS_MONGODB_EXCEPTION"})
    else:
        return uid
