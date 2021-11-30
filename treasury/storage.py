from celery_worker.locks import get_mongodb_collection
from environment_settings import (
    TREASURY_CONTEXT_COLLECTION, TREASURY_DB_NAME, TREASURY_ORG_COLLECTION, TREASURY_XML_TEMPLATES_COLLECTION,
)
from pymongo.errors import PyMongoError
from pymongo import UpdateOne, DeleteMany
from celery.signals import celeryd_init
from celery.utils.log import get_task_logger
from celery_worker.celery import app
from typing import List, Dict
from http import HTTPStatus
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


def save_xml_template(task, contract_id, data, xml_was_changed=False):
    if isinstance(data, bytes):
        data = data.decode('windows-1251')
    try:
        get_collection(collection_name=TREASURY_XML_TEMPLATES_COLLECTION).update_one(
            {"contract_id": contract_id, "xml_changed": xml_was_changed},
            {"$set": {"xml_data": data}},
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


def insert_one(collection_name, data: Dict):
    try:
        coll = get_collection(collection_name=collection_name)
        doc = coll.insert_one(data)
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        return {"status": HTTPStatus.SERVICE_UNAVAILABLE, "data": "MONGODB ACCESS ERROR"}
    else:
        logger.info(f"{data} has been inserted")
        return {"status": HTTPStatus.CREATED, "data": doc.inserted_id}


def insert_many(collection_name, data: List[Dict]):
    try:
        coll = get_collection(collection_name=collection_name)
        coll.insert_many(data)
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_ERROR"})
        return {"status": HTTPStatus.SERVICE_UNAVAILABLE, "data": "MONGODB ACCESS ERROR"}
    else:
        logger.info(f"{data} has been inserted")
        return {"status": HTTPStatus.CREATED}
