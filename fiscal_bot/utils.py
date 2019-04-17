from celery_worker.locks import get_mongodb_collection
from pymongo.errors import PyMongoError
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def get_increment_id(task, uid):
    """
    We need to store two increment ids
    which should be reset daily and monthly.
    So this is the base function for this functionality
    :param task:
    :param uid:
    :return:
    """
    collection = get_mongodb_collection("fiscal_bot_document_increments")

    try:
        result = collection.find_and_modify(
            query={'_id': uid},
            update={"$inc": {'count': 1}},
            new=True,
            upsert=True,
        )
    except PyMongoError as e:
        logger.exception(e, extra={"MESSAGE_ID": "MONGODB_ACCESS_FISCAL_INCREMENT_ERROR"})
        raise task.retry()
    else:
        return result["count"]


def get_daily_increment_id(task, date):
    return get_increment_id(task, str(date))


def get_monthly_increment_id(task, date):
    hyp = "-"
    month_str = hyp.join(str(date).split(hyp)[:2])  # 2019-03-31 -> "2019-03"
    return get_increment_id(task, month_str)
