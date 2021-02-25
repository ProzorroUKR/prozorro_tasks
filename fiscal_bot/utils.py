import sys
from celery_worker.locks import get_mongodb_collection
from celery_worker.celery import app
from pymongo.errors import PyMongoError
from celery.utils.log import get_task_logger
from celery.signals import celeryd_init
from datetime import datetime
from environment_settings import FISCAL_BOT_CHECK_RECEIPT_TASKS_COLLECTION

logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=20)
def create_check_receipt_tasks_collection_index(self):
    expire_after_seconds = 86400 * 30  # each document expires after 30 days
    try:
        get_mongodb_collection(FISCAL_BOT_CHECK_RECEIPT_TASKS_COLLECTION).create_index(
            "creationDate", expireAfterSeconds=expire_after_seconds
        )
    except PyMongoError as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        raise self.retry()


if "test" not in sys.argv[0]:  # pragma: no cover
    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        create_check_receipt_tasks_collection_index.delay()


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


def save_check_receipt_task_info(
        tender_id, task_id, has_called_new_check_receipt_task=False, receipt_file_successfully_saved=False
):
    collection = get_mongodb_collection(FISCAL_BOT_CHECK_RECEIPT_TASKS_COLLECTION)

    collection.update_one(
        {
            "tenderId": tender_id,
            "checkForResponseFileTaskId": task_id
        },
        {
            "$set": {
                "hasCalledNewCheckReceiptTask": has_called_new_check_receipt_task,
                "receiptFileSuccessfullySaved": receipt_file_successfully_saved,
                "creationDate": datetime.utcnow()
             }
        },
        upsert=True,
    )


def get_check_receipt_tasks_info_by_tender_id(tender_id):

    collection = get_mongodb_collection(FISCAL_BOT_CHECK_RECEIPT_TASKS_COLLECTION)
    return collection.find({"tenderId": tender_id})


def get_check_receipt_task_info_by_id(task_id):

    collection = get_mongodb_collection(FISCAL_BOT_CHECK_RECEIPT_TASKS_COLLECTION)
    return collection.find_one({"checkForResponseFileTaskId": task_id})
