from unittest.mock import patch, MagicMock
from datetime import datetime
from pymongo.errors import NetworkTimeout
from celery_worker.locks import args_to_uid
from edr_bot.results_db import (
    get_upload_results,
    save_upload_results,
    set_upload_results_attached,
)
import unittest


class ResultsDBTestCase(unittest.TestCase):

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
