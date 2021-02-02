from celery.utils.log import get_task_logger
from pymongo.errors import PyMongoError

from celery_worker.locks import get_mongodb_collection, FEED_DATE_MODIFIED_LOCK_COLLECTION_NAME

logger = get_task_logger(__name__)


def put_date_modified_lock(resource):
    collection = get_mongodb_collection(FEED_DATE_MODIFIED_LOCK_COLLECTION_NAME)
    try:
        collection.update_one(
            {"resource": resource},
            {"$set": {"locked": True}},
            upsert=True,
        )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FEED_PUT_DATE_MODIFIED_LOCK_MONGODB_EXCEPTION"})


def update_date_modified_lock(resource, date_modified):
    collection = get_mongodb_collection(FEED_DATE_MODIFIED_LOCK_COLLECTION_NAME)
    try:
        doc = collection.find_one({"resource": resource})
        if date_modified and (not doc or not doc.get("locked")):
            collection.update_one(
                {"resource": resource},
                {"$set": {"dateModified": date_modified, "locked": False}},
                upsert=True,
            )
    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FEED_UPDATE_DATE_MODIFIED_LOCK_MONGODB_EXCEPTION"})


def handle_date_modified_lock(resource, date_modified):
    collection = get_mongodb_collection(FEED_DATE_MODIFIED_LOCK_COLLECTION_NAME)
    try:
        doc = collection.find_one({"resource": resource})
        lock_date_modified = doc.get("dateModified") if doc else None
        if date_modified and lock_date_modified and date_modified < lock_date_modified:
            collection.update_one(
                {"resource": resource},
                {"$set": {"locked": False}},
                upsert=True,
            )
            return True

    except PyMongoError as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FEED_HANDLE_MODIFIED_LOCK_MONGODB_EXCEPTION"})

    return False
