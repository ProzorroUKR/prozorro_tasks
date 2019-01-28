from functools import wraps
from datetime import datetime
from celery_worker.celery import app
from celery.utils.log import get_task_logger
from celery.signals import celeryd_init
from celery.app.task import Task
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError
from environment_settings import (
    MONGODB_URL, MONGODB_DATABASE,
    MONGODB_SERVER_SELECTION_TIMEOUT,
    MONGODB_CONNECT_TIMEOUT,
    MONGODB_SOCKET_TIMEOUT
)
import hashlib
import sys

logger = get_task_logger(__name__)
MONGODB_UID_LENGTH = 24


def get_mongodb_collection(collection_name="celery_worker_locks"):
    client = MongoClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT * 1000,
        connectTimeoutMS=MONGODB_CONNECT_TIMEOUT * 1000,
        socketTimeoutMS=MONGODB_SOCKET_TIMEOUT * 1000,
        retryWrites=True
    )
    db = getattr(client, MONGODB_DATABASE)
    collection = getattr(db, collection_name)
    return collection


@app.task(bind=True)
def init_lock_index(self):
    # https://docs.mongodb.com/manual/tutorial/expire-data/
    try:
        get_mongodb_collection().create_index(
            "createdAt",
            expireAfterSeconds=30 * 60  # delete index if you've changed this
        )
    except OperationFailure as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        return "exists"
    except PyMongoError as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR"})
        raise self.retry()
    return "success"


if "test" not in sys.argv[0]:  # pragma: no cover

    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        init_lock_index.delay()


def hash_string_to_uid(input_string):
    h = hashlib.shake_256()
    h.update(input_string.encode("utf-8"))
    return h.hexdigest(int(MONGODB_UID_LENGTH / 2))


def args_to_uid(args):
    args_string = "".join((str(a) for a in args))
    uid = hash_string_to_uid(args_string)
    return uid


def unique_task_decorator(task):
    """
    Ensure that no more than a single unique task (task name + its args)
    is executed in a defined period (expireAfterSeconds)
    We use https://docs.mongodb.com/manual/tutorial/expire-data/ to store keys
    :param task:
    :return:
    """

    @wraps(task)
    def unique_task(*args, **kwargs):

        if args and isinstance(args[0], Task):  # @app.task(bind=True)
            self = args[0]
            key_args = args[1:]
        else:
            self, key_args = None, args

        task_uid = args_to_uid(
            (task.__name__, key_args, kwargs)
        )
        collection = get_mongodb_collection()
        try:
            doc = collection.find_one(
                {'_id': task_uid}
            )
        except PyMongoError as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "UNIQUE_TASK_GET_RESULTS_MONGODB_EXCEPTION"})

            if self is None:
                logger.warning("Cannot retry task, skipping it's duplicate check",
                               extra={"MESSAGE_ID": "UNIQUE_TASK_MONGODB_EXCEPTION_CANNOT_RETRY"})
                doc = None
            else:
                raise self.retry()

        if doc is not None:
            logger.warning(
                "Stopping a duplicate of task {} with {} {}".format(task.__name__, key_args, kwargs),
                extra={"MESSAGE_ID": "UNIQUE_TASK_DUPLICATE_STOPPING"}
            )
            return {"error": "Duplicate task execution is cancelled"}

        # executing the task
        task_response = task(*args, **kwargs)

        # task is successfully finished, add task marker to mongodb
        try:
            collection.insert({
                '_id': task_uid,
                'createdAt': datetime.utcnow(),
            })
        except PyMongoError as exc:
            logger.exception(exc, extra={"MESSAGE_ID": "UNIQUE_TASK_POST_RESULTS_MONGODB_EXCEPTION"})
        finally:
            return task_response

    return unique_task
