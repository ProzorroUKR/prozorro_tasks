from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
from pymongo.errors import ConnectionFailure
from celery_worker.celery import app
from celery_worker.locks import (
    hash_string_to_uid,
    MONGODB_UID_LENGTH,
    args_to_uid,
    get_mongodb_collection,
    unique_task,
)
from environment_settings import (
    MONGODB_URL, MONGODB_DATABASE,
    MONGODB_SERVER_SELECTION_TIMEOUT,
    MONGODB_CONNECT_TIMEOUT,
    MONGODB_SOCKET_TIMEOUT
)
import unittest


class LocksTestCase(unittest.TestCase):

    @patch("celery_worker.locks.MongoClient")
    def test_get_mongodb_collection(self, mongodb_client):
        client = MagicMock()
        getattr(client, MONGODB_DATABASE).celery_worker_locks = 13
        mongodb_client.return_value = client

        return_value = get_mongodb_collection()

        mongodb_client.assert_called_once_with(
            MONGODB_URL,
            serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT * 1000,
            connectTimeoutMS=MONGODB_CONNECT_TIMEOUT * 1000,
            socketTimeoutMS=MONGODB_SOCKET_TIMEOUT * 1000,
            retryWrites=True
        )
        self.assertEqual(return_value, 13)

    def test_hash_string_to_uid(self):
        test_1 = "qwerty 123456"
        self.assertEqual(
            hash_string_to_uid(test_1),
            hash_string_to_uid(test_1)
        )

        test_2 = "qwёrty 123456"
        self.assertNotEqual(
            hash_string_to_uid(test_1),
            hash_string_to_uid(test_2)
        )

        result = hash_string_to_uid(test_1)
        self.assertEqual(len(result), MONGODB_UID_LENGTH)

        result = hash_string_to_uid((test_1 + test_2) * 10)
        self.assertEqual(len(result), MONGODB_UID_LENGTH)

    def test_args_to_uid(self):
        result1 = args_to_uid((1, 2, [3, 4], "hello"))
        result2 = args_to_uid((1, 2, [3, 4], "hello"))
        self.assertEqual(result1, result2)

        result3 = args_to_uid((12, [3, 4], "hello"))
        self.assertEqual(result1, result3)

        result4 = args_to_uid((1, 3, [3, 4], "hello"))
        self.assertNotEqual(result1, result4)

        result5 = args_to_uid(
            ({"test": 1, "hello": [1, 2]},)
        )
        result6 = args_to_uid(
            ({"test": 1, "hello": [1, 2]},)
        )

        self.assertEqual(result5, result6)

        result7 = args_to_uid(
            ({"test": 1, "hello": [1, 2]},)
        )
        result8 = args_to_uid(
            ({"test": 1, "hello": [1, 2, 3]},)
        )

        self.assertNotEqual(result7, result8)

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_unique_task_decorator_no_duplicate(self, get_collection):
        get_collection.return_value.find_one.return_value = None

        test_method_procedure = Mock()

        # create decorated function
        @unique_task
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            # run it
            test_method(1, 2, message="Hi")

        # check that decorator checked the lock and set it
        task_uid = args_to_uid(
            ("celery_worker.tests.test_locks", "test_method", (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.find_one.assert_called_once_with(
            {"_id": task_uid}
        )
        test_method_procedure.assert_called_once_with(1, 2, message="Hi")
        get_collection.return_value.insert.assert_called_once_with(
            {"_id": task_uid, "createdAt": datetime_mock.utcnow.return_value}
        )

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_unique_task_decorator_duplicate_detected(self, get_collection):
        get_collection.return_value.find_one.return_value = {"Achtung": "!"}

        test_method_procedure = Mock()

        # create decorated function
        @unique_task
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            # run it
            test_method(1, 2, message="Hi")

        # check that decorator checked the lock and set it
        task_uid = args_to_uid(
            ("celery_worker.tests.test_locks", "test_method", (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.find_one.assert_called_once_with(
            {"_id": task_uid}
        )
        test_method_procedure.assert_not_called()
        get_collection.return_value.insert.assert_not_called()

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_unique_task_decorator_mongodb_get_exc(self, get_collection):
        get_collection.return_value.find_one.side_effect = ConnectionFailure()

        test_method_procedure = Mock()

        # create decorated function
        @unique_task
        def test_method(*args, **kwargs):
            test_method_procedure(*args, **kwargs)

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            # run it
            test_method(1, 2, message="Hi")

        # check that decorator checked the lock and set it
        task_uid = args_to_uid(
            ("celery_worker.tests.test_locks", "test_method", (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.find_one.assert_called_once_with(
            {"_id": task_uid}
        )
        test_method_procedure.assert_called_once_with(1, 2, message="Hi")
        get_collection.return_value.insert.assert_called_once_with(
            {"_id": task_uid, "createdAt": datetime_mock.utcnow.return_value}
        )

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_unique_task_decorator_mongodb_get_exc_for_bind_task(self, get_collection):
        get_collection.return_value.find_one.side_effect = ConnectionFailure()

        test_method_procedure = Mock()

        # create decorated function
        @app.task(bind=True)
        @unique_task
        def test_method(self, *args, **kwargs):
            test_method_procedure(*args, **kwargs)

        class RetryException(Exception):
            pass

        test_method.retry = RetryException

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            # run it
            with self.assertRaises(RetryException):
                test_method(1, 2, message="Hi")

        # check that decorator checked the lock and set it
        task_uid = args_to_uid(
            ("celery_worker.tests.test_locks", "test_method", (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.find_one.assert_called_once_with(
            {"_id": task_uid}
        )
        test_method_procedure.assert_not_called()
        get_collection.return_value.insert.assert_not_called()

    @patch("celery_worker.locks.get_mongodb_collection")
    def test_unique_task_decorator_for_bind_task(self, get_collection):
        get_collection.return_value.find_one.return_value = None

        test_method_procedure = Mock()

        # create decorated function
        @app.task(bind=True)
        @unique_task
        def test_method(self, *args, **kwargs):
            test_method_procedure(self, *args, **kwargs)

        class RetryException(Exception):
            pass

        test_method.retry = RetryException

        with patch("celery_worker.locks.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()

            # run it
            test_method(1, 2, message="Hi")

        # check that decorator checked the lock and set it
        task_uid = args_to_uid(
            ("celery_worker.tests.test_locks", "test_method", (1, 2), dict(message="Hi"))
        )
        get_collection.return_value.find_one.assert_called_once_with(
            {"_id": task_uid}
        )
        test_method_procedure.assert_called_once_with(test_method, 1, 2, message="Hi")
        get_collection.return_value.insert.assert_called_once_with(
            {"_id": task_uid, "createdAt": datetime_mock.utcnow.return_value}
        )


