from unittest.mock import patch, MagicMock
from datetime import datetime
from pymongo.errors import NetworkTimeout
from fiscal_bot.utils import get_increment_id, get_daily_increment_id, get_monthly_increment_id
import unittest


class GetIncrementTestCase(unittest.TestCase):

    @patch("fiscal_bot.utils.get_increment_id")
    def test_get_success_daily(self, get_increment_id_mock):
        get_increment_id_mock.return_value = 13

        task = MagicMock()
        today = datetime(2019, 4, 1).date()

        result = get_daily_increment_id(task, today)

        self.assertEqual(result, 13)
        get_increment_id_mock.assert_called_once_with(
            task,
            "2019-04-01"
        )

    @patch("fiscal_bot.utils.get_increment_id")
    def test_get_success_monthly(self, get_increment_id_mock):
        get_increment_id_mock.return_value = 130

        task = MagicMock()
        today = datetime(2019, 4, 1).date()

        result = get_monthly_increment_id(task, today)

        self.assertEqual(result, 130)
        get_increment_id_mock.assert_called_once_with(
            task,
            "2019-04"
        )

    @patch("fiscal_bot.utils.get_mongodb_collection")
    def test_get_success(self, get_collection):
        task = MagicMock()

        collection = MagicMock()
        collection.find_and_modify.return_value = {"count": 13}
        get_collection.return_value = collection

        result = get_increment_id(task, "test_uid")

        self.assertEqual(result, 13)
        collection.find_and_modify.assert_called_once_with(
            query={'_id': "test_uid"},
            update={"$inc": {'count': 1}},
            new=True,
            upsert=True,
        )

    @patch("fiscal_bot.utils.get_mongodb_collection")
    def test_get_upload_results_raise_exc(self, get_collection):
        class RetryException(Exception):
            pass

        task = MagicMock()
        task.retry = RetryException

        collection = MagicMock()
        collection.find_and_modify.side_effect = NetworkTimeout
        get_collection.return_value = collection

        with self.assertRaises(RetryException):
            get_increment_id(task, "test_uid")

        collection.find_and_modify.assert_called_once_with(
            query={'_id': "test_uid"},
            update={"$inc": {'count': 1}},
            new=True,
            upsert=True,
        )
