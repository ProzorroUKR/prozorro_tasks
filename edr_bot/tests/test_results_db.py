from unittest.mock import patch, MagicMock
from datetime import datetime
from pymongo.errors import NetworkTimeout
from edr_bot.results_db import (
    get_mongodb_collection, hash_string_to_uid, MONGODB_UID_LENGTH, args_to_uid,
    get_upload_results, save_upload_results, set_upload_results_attached
)
from edr_bot.settings import (
    MONGODB_SERVER_SELECTION_TIMEOUT,
    MONGODB_CONNECT_TIMEOUT,
    MONGODB_SOCKET_TIMEOUT
)
from environment_settings import MONGODB_URL
import unittest


class ResultsDBTestCase(unittest.TestCase):

    @patch("edr_bot.results_db.MongoClient")
    def test_get_mongodb_collection(self, mongodb_client):
        client = MagicMock()
        client.erd_bot.upload_results = 13
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

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_get_upload_results(self, get_collection):
        task = MagicMock()

        collection = MagicMock()
        collection.find_one.return_value = {"hello": "there"}
        get_collection.return_value = collection

        args = (1, "two", 3)
        result = get_upload_results(task, *args)

        self.assertEqual(result, {"hello": "there"})
        collection.find_one.assert_called_once_with({'_id': args_to_uid(args)})

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_get_upload_results_raise_exc(self, get_collection):

        class RetryException(Exception):
            pass

        task = MagicMock()
        task.retry = RetryException

        collection = MagicMock()
        collection.find_one.side_effect = NetworkTimeout
        get_collection.return_value = collection

        args = (1, "two", 3)
        with self.assertRaises(RetryException):
            get_upload_results(task, *args)

        collection.find_one.assert_called_once_with({'_id': args_to_uid(args)})

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_save_upload_results(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        file_data = {"data": 1, "meta": "hello"}
        args = ("one", 2, [3, 4])

        with patch("edr_bot.results_db.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()
            result = save_upload_results(file_data, *args)

        collection.insert.assert_called_once_with(
            {
                '_id': args_to_uid(args),
                'file_data': file_data,
                'createdAt': datetime_mock.utcnow.return_value
            }
        )
        self.assertEqual(result, args_to_uid(args))

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_save_upload_results_raise_exc(self, get_collection):
        collection = MagicMock()
        collection.insert.side_effect = NetworkTimeout()
        get_collection.return_value = collection

        file_data = {"data": 1, "meta": "hello"}
        args = ("one", 2, [3, 4])

        with patch("edr_bot.results_db.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()
            result = save_upload_results(file_data, *args)

        collection.insert.assert_called_once_with(
            {
                '_id': args_to_uid(args),
                'file_data': file_data,
                'createdAt': datetime_mock.utcnow.return_value
            }
        )
        self.assertIs(result, None)

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_set_upload_results_attached(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        args = ("one", 2, {3: 4, 5: 6})

        result = set_upload_results_attached(*args)

        collection.update_one.assert_called_once_with(
            {'_id': args_to_uid(args)},
            {"$set": {'attached': True}}
        )
        self.assertEqual(result, args_to_uid(args))

    @patch("edr_bot.results_db.get_mongodb_collection")
    def test_set_upload_results_attached_raise_exc(self, get_collection):
        collection = MagicMock()
        collection.update_one.side_effect = NetworkTimeout()
        get_collection.return_value = collection

        args = ("one", 2, {3: 4, 5: 6})

        result = set_upload_results_attached(*args)

        collection.update_one.assert_called_once_with(
            {'_id': args_to_uid(args)},
            {"$set": {'attached': True}}
        )
        self.assertIs(result, None)
