from unittest.mock import patch, MagicMock, ANY

from pymongo.errors import DuplicateKeyError

import unittest

from autoclient_payments.results_db import (
    get_payment_item,
    push_payment_message,
    save_payment_item,
    data_to_uid,
    set_payment_params,
    set_payment_resolution,
    get_payment_item_by_params,
    get_last_transaction,
)
from autoclient_payments.tests.conftest import TRANSACTION_DATA


class ResultsDBTestCase(unittest.TestCase):
    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_get_payment_item(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        uid = "test_uid"

        result = get_payment_item(uid)

        self.assertEqual(result, collection.find_one.return_value)
        collection.find_one.assert_called_once_with({"_id": uid})

    @patch("autoclient_payments.results_db.datetime")
    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_push_payment_message(self, get_collection, datetime):
        collection = MagicMock()
        get_collection.return_value = collection

        fake_datetime = "test_datetime"
        datetime.utcnow.return_value = fake_datetime

        message = "Test message"
        message_id = "TEST_MESSAGE_ID"

        result = push_payment_message(TRANSACTION_DATA, message_id, message)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(
            ANY, {"$push": {"messages": {"message_id": message_id, "message": message, "createdAt": fake_datetime}}}
        )

    @patch("autoclient_payments.results_db.TIMEZONE")
    @patch("autoclient_payments.results_db.datetime")
    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_save_payment_item(self, get_collection, datetime, TIMEZONE):
        collection = MagicMock()
        get_collection.return_value = collection

        fake_datetime = "test_datetime"
        datetime.utcnow.return_value = fake_datetime
        TIMEZONE.localize.return_value.isoformat.return_value = fake_datetime

        user = "test_user"

        result = save_payment_item(TRANSACTION_DATA, user)

        self.assertEqual(result, collection.insert_one.return_value)
        collection.insert_one.assert_called_once_with(
            {
                "_id": data_to_uid(TRANSACTION_DATA),
                "payment": TRANSACTION_DATA,
                "user": user,
                "dateOper": fake_datetime,
                "createdAt": fake_datetime,
            }
        )

    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_save_payment_item_duplicate(self, get_collection):
        collection = MagicMock()
        collection.insert_one.side_effect = DuplicateKeyError("error")
        get_collection.return_value = collection

        user = "test_user"

        result = save_payment_item(TRANSACTION_DATA, user)

        self.assertEqual(result, None)

    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_set_payment_params(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        params = {"test_param": "test_value"}

        result = set_payment_params(TRANSACTION_DATA, params)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(ANY, {"$set": {"params": params}})

    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_set_payment_resolution(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        params = {"test_param": "test_value"}

        result = set_payment_resolution(TRANSACTION_DATA, params)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(ANY, {"$set": {"resolution": params}})

    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_get_payment_item_by_params(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        params = {"test_param": "test_value"}

        result = get_payment_item_by_params(params)

        self.assertEqual(result, collection.find_one.return_value)
        collection.find_one.assert_called_once_with({"$and": [{"params.test_param": "test_value"}]})

    @patch("autoclient_payments.results_db.get_mongodb_collection")
    def test_get_last_transaction(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection
        result = get_last_transaction()
        self.assertEqual(result, collection.find_one.return_value)
        collection.find_one.assert_called_once_with({}, sort=[("dateOper", -1)])
