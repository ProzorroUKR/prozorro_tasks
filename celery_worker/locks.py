from functools import wraps
from datetime import datetime, timedelta
from celery_worker.celery import app
from celery.utils.log import get_task_logger
from celery.signals import celeryd_init
from celery.app.task import Task
from celery.exceptions import MaxRetriesExceededError
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
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


DUPLICATE_COLLECTION_NAME = "celery_worker_locks"
LOCK_COLLECTION_NAME = "celery_worker_concurrency_locks"


def get_mongodb_collection(collection_name=DUPLICATE_COLLECTION_NAME):
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


# https://docs.mongodb.com/manual/tutorial/expire-data/

@app.task(bind=True, max_retries=20)
def init_duplicate_index(self):
    try:
        get_mongodb_collection(DUPLICATE_COLLECTION_NAME).create_index(
            "createdAt",
            expireAfterSeconds=30 * 60  # delete index if you've changed this
        )
    except PyMongoError as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        raise self.retry()


@app.task(bind=True, max_retries=20)
def init_concurrency_lock_index(self):
    try:
        get_mongodb_collection(LOCK_COLLECTION_NAME).create_index("expireAt", expireAfterSeconds=0)
    except PyMongoError as e:
        logger.exception(e,  extra={"MESSAGE_ID": "MONGODB_INDEX_CREATION_ERROR"})
        raise self.retry()


if "test" not in sys.argv[0]:  # pragma: no cover
    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        init_duplicate_index.delay()

    @celeryd_init.connect
    def task_sent_handler(*args, **kwargs):
        init_concurrency_lock_index.delay()


def hash_string_to_uid(input_string):
    h = hashlib.shake_256()
    h.update(input_string.encode("utf-8"))
    return h.hexdigest(int(MONGODB_UID_LENGTH / 2))


def args_to_uid(args):
    args_string = "".join((str(a) for a in args))
    uid = hash_string_to_uid(args_string)
    return uid


# skip_duplicates
def unique_task_decorator(task):
    """
    Use this one to avoid duplicate tasks execution.
    It discards duplicates after the original task is successfully finished.
    There still may be duplicates in case a duplicate task starts before the first task(original) finishes.
    """

    @wraps(task)
    def unique_task(*args, **kwargs):

        if args and isinstance(args[0], Task):  # @app.task(bind=True)
            self = args[0]
            key_args = args[1:]
        else:
            self, key_args = None, args

        task_uid = args_to_uid(
            (task.__module__, task.__name__, key_args, kwargs)
        )
        collection = get_mongodb_collection(DUPLICATE_COLLECTION_NAME)
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


def concurrency_lock(*args, **kwargs):
    """
    Use this task decorator to avoid concurrent execution of duplicate tasks
    it won't discard any tasks, only reschedule their execution

    :param kwargs:
        timeout - how long to prevent duplicates to run. 60sec will be added because of mongodb ttl interval

    Example:
        @app.task(bind=True)
        @concurrency_lock
        def echo_task(self):
            pass

        or

        @app.task(bind=True)
        @concurrency_lock(timeout=30)
        def echo_task(self):
            pass
    """

    def lock_decorator(task):
        @wraps(task)
        def wrapper(*args, **kwargs):
            assert len(args) > 0, "Expected to used with bind tasks"
            self, *task_args = args  # *task_args creates a list instance, so I'll convert it to tuple
            assert isinstance(self, Task), "Expected to used with bind tasks"
            task_uid = args_to_uid((task.__module__, task.__name__, tuple(task_args), kwargs))

            collection = get_mongodb_collection(LOCK_COLLECTION_NAME)
            try:
                collection.insert_one(
                    {'_id': task_uid, 'expireAt': datetime.utcnow() + timedelta(seconds=concurrency_timeout)}
                )
            except PyMongoError as exc:  # expect DuplicateKeyError, but should handle also connection problems
                retry_kw = dict(max_retries=20)
                if isinstance(exc, DuplicateKeyError):
                    # From Mongodb docs: The background task that removes expired documents runs every 60 seconds
                    retry_kw["countdown"] = concurrency_timeout + 60
                try:
                    self.retry(**retry_kw)
                except MaxRetriesExceededError:
                    logger.exception(exc)  # if retry limit is exceed, we allow the task to be executed

            task(*args, **kwargs)

        return wrapper

    if len(args) == 1 and callable(args[0]):
        concurrency_timeout = 10
        return lock_decorator(args[0])
    elif "timeout" in kwargs:
        concurrency_timeout = float(kwargs.get("timeout"))
        return lock_decorator
    else:
        raise NotImplementedError("Unexpected use")
