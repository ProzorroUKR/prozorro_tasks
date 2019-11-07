from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from celery.exceptions import Retry, MaxRetriesExceededError
from celery_worker.celery import app
from celery_worker.locks import args_to_uid, concurrency_lock
import unittest


@app.task
def dummy_task(self):
    pass


class ConcurrencyLockTestCase(unittest.TestCase):

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_success(self, get_collection):
        get_collection.return_value.insert_one.return_value = None

        test_method_procedure = Mock()

        @concurrency_lock
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            test_method(dummy_task, 1, 2, message="Hi")  # run

        task_uid = args_to_uid(
            (test_method.__module__, test_method.__name__, (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.insert_one.assert_called_once_with(
            {
                "_id": task_uid,
                "expireAt": datetime_mock.utcnow.return_value + timedelta(seconds=10)
            }
        )
        test_method_procedure.assert_called_once_with(dummy_task, 1, 2, message="Hi")

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_duplicate_exc(self, get_collection):
        """
        in case of lock retry later after lock timeout
        """
        get_collection.return_value.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key error collection")
        test_method_procedure = Mock()

        @concurrency_lock
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        dummy_task.retry = Mock(side_effect=Retry)
        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            with self.assertRaises(Retry):
                test_method(dummy_task)  # run

        task_uid = args_to_uid(
            (test_method.__module__, test_method.__name__, tuple(), dict())
        )
        get_collection.return_value.insert_one.assert_called_once_with(
            {
                "_id": task_uid,
                "expireAt": datetime_mock.utcnow.return_value + timedelta(seconds=10)
            }
        )
        dummy_task.retry.assert_called_once_with(max_retries=20, countdown=70)
        test_method_procedure.assert_not_called()

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_mongodb_exc(self, get_collection):
        """
        in case of mongodb connection error task should be retried
        """
        get_collection.return_value.insert_one.side_effect = ConnectionFailure
        test_method_procedure = Mock()

        @concurrency_lock
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        dummy_task.retry = Mock(side_effect=Retry)
        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            with self.assertRaises(Retry):
                test_method(dummy_task)  # run

        task_uid = args_to_uid(
            (test_method.__module__, test_method.__name__, tuple(), dict())
        )
        get_collection.return_value.insert_one.assert_called_once_with(
            {
                "_id": task_uid,
                "expireAt": datetime_mock.utcnow.return_value + timedelta(seconds=10)
            }
        )
        dummy_task.retry.assert_called_once_with(max_retries=20)
        test_method_procedure.assert_not_called()

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_max_reties_exceed(self, get_collection):
        """
        in case of too many reties because of mongodb errors the max_retry limit may exceed
        we should run task then
        """
        get_collection.return_value.insert_one.side_effect = ConnectionFailure
        test_method_procedure = Mock()

        @concurrency_lock
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        dummy_task.retry = Mock(side_effect=MaxRetriesExceededError)
        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            test_method(dummy_task)  # run

        task_uid = args_to_uid(
            (test_method.__module__, test_method.__name__, tuple(), dict())
        )
        get_collection.return_value.insert_one.assert_called_once_with(
            {
                "_id": task_uid,
                "expireAt": datetime_mock.utcnow.return_value + timedelta(seconds=10)
            }
        )
        dummy_task.retry.assert_called_once_with(max_retries=20)
        test_method_procedure.assert_called_once_with(dummy_task)
