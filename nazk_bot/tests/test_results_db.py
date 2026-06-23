from unittest.mock import patch, MagicMock
from datetime import datetime
from pymongo.errors import NetworkTimeout
from celery_worker.locks import args_to_uid
from nazk_bot.results_db import save_upload_results
import unittest


class ResultsDBTestCase(unittest.TestCase):

    @patch("nazk_bot.results_db.get_mongodb_collection")
    def test_save_upload_results(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        file_data = {"data": 1, "meta": "hello"}
        args = ("one", 2, [3, 4])

        with patch("nazk_bot.results_db.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()
            result = save_upload_results(file_data, *args)

        collection.insert_one.assert_called_once_with(
            {
                '_id': args_to_uid(args),
                'file_data': file_data,
                'createdAt': datetime_mock.utcnow.return_value
            }
        )
        self.assertEqual(result, args_to_uid(args))

    @patch("nazk_bot.results_db.get_mongodb_collection")
    def test_save_upload_results_raise_exc(self, get_collection):
        collection = MagicMock()
        collection.insert_one.side_effect = NetworkTimeout()
        get_collection.return_value = collection

        file_data = {"data": 1, "meta": "hello"}
        args = ("one", 2, [3, 4])

        with patch("nazk_bot.results_db.datetime") as datetime_mock:
            datetime_mock.utcnow.return_value = datetime.utcnow()
            result = save_upload_results(file_data, *args)

        collection.insert_one.assert_called_once_with(
            {
                '_id': args_to_uid(args),
                'file_data': file_data,
                'createdAt': datetime_mock.utcnow.return_value
            }
        )
        self.assertIs(result, None)
