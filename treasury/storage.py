from celery_worker.locks import get_mongodb_collection
from environment_settings import TREASURY_CONTEXT_COLLECTION, TREASURY_DB_NAME, TREASURY_ORG_COLLECTION
from pymongo.errors import PyMongoError
from pymongo import UpdateOne, DeleteMany
from celery.signals import celeryd_init
from celery.utils.log import get_task_logger
from celery_worker.celery import app
import sys


logger = get_task_logger(__name__)


ORG_UNIQUE_FIELD = "edrpou_code"


def get_collection(collection_name=TREASURY_CONTEXT_COLLECTION):
    return get_mongodb_collection(
        collection_name=collection_name,
        db_name=TREASURY_DB_NAME,
    )


@app.task(bind=True, max_retries=20)
def init_organisations_index(self):
    try:
        get_collection(TREASURY_ORG_COLLECTION).create_index(ORG_UNIQUE_FIELD)
    except PyMongoError as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        raise self.retry()


if "test" not in sys.argv[0]:  # pragma: no cover
    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        init_organisations_index.delay()


def get_contract_context(task, contract_id):
    try:
        doc = get_collection().find_one({"_id": contract_id})
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        raise task.retry()
    else:
        if doc:
            return doc.get("context")


def save_contract_context(task, contract_id, data):
    try:
        get_collection().update_one(
            {"_id": contract_id},
            {"$set": {"context": data}},
            upsert=True
        )
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        raise task.retry()


def update_organisations(task, records):
    collection = get_collection(collection_name=TREASURY_ORG_COLLECTION)
    operations = []
    codes = []
    for org in records:
        code = org[ORG_UNIQUE_FIELD]
        codes.append(code)
        operations.append(UpdateOne({ORG_UNIQUE_FIELD: code}, {"$set": org}, upsert=True))

    if codes:
        operations.append(
            DeleteMany({ORG_UNIQUE_FIELD: {"$nin": codes}})  # delete codes not on the list
        )

    try:
        result = collection.bulk_write(operations)
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        raise task.retry()
    else:
        return result.bulk_api_result


def get_organisation(task, code):
    collection = get_collection(collection_name=TREASURY_ORG_COLLECTION)
    try:
        result = collection.find_one({ORG_UNIQUE_FIELD: code})
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        raise task.retry()
    else:
        return result
