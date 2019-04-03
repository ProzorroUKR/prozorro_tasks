from unittest.mock import patch, MagicMock
from datetime import datetime
from pymongo.errors import NetworkTimeout
from fiscal_bot.utils import get_increment_id
import unittest


class GetIncrementTestCase(unittest.TestCase):

    @patch("fiscal_bot.utils.get_mongodb_collection")
    def test_get_success(self, get_collection):
        task = MagicMock()
        today = datetime.now().date()

        collection = MagicMock()
        collection.find_and_modify.return_value = {"count": 13}
        get_collection.return_value = collection

        result = get_increment_id(task, today)

        self.assertEqual(result, 13)
        collection.find_and_modify.assert_called_once_with(
            query={'_id': str(today)},
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

        today = datetime.now().date()

        collection = MagicMock()
        collection.find_and_modify.side_effect = NetworkTimeout
        get_collection.return_value = collection

        with self.assertRaises(RetryException):
            get_increment_id(task, today)

        collection.find_and_modify.assert_called_once_with(
            query={'_id': str(today)},
            update={"$inc": {'count': 1}},
            new=True,
            upsert=True,
        )
