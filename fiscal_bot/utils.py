from celery_worker.locks import get_mongodb_collection
from pymongo.errors import PyMongoError
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def get_increment_id(task, date):
    collection = get_mongodb_collection("fiscal_bot_document_increments")

    try:
        result = collection.find_and_modify(
            query={'_id': str(date)},
            update={"$inc": {'count': 1}},
            new=True,
            upsert=True,
        )
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_FISCAL_INCREMENT_ERROR"})
        raise task.retry()
    else:
        return result["count"]
