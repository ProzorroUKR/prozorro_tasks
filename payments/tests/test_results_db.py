from unittest.mock import patch, MagicMock, ANY

from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

import unittest

from payments.results_db import (
    get_payment_count,
    get_payment_list,
    get_payment_item,
    push_payment_message,
    save_payment_item,
    data_to_uid,
    set_payment_params,
    set_payment_resolution,
    get_payment_item_by_params,
)


class ResultsDBTestCase(unittest.TestCase):

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_count(self, get_collection):
        collection = MagicMock()
        collection.count_documents.return_value = 1
        get_collection.return_value = collection

        filters = {"some_filter": "some_filter_value"}

        result = get_payment_count(filters)

        self.assertEqual(result, 1)
        collection.count_documents.assert_called_once_with(filters)

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_list(self, get_collection):
        cursor = MagicMock()
        cursor.sort.return_value = cursor

        collection = MagicMock()
        collection.find.return_value = cursor
        get_collection.return_value = collection

        filters = {"some_filter": "some_filter_value"}

        result = get_payment_list(filters)

        self.assertEqual(result, cursor)
        collection.find.assert_called_once_with(filters)
        cursor.sort.assert_called_once_with("createdAt", DESCENDING)

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_list_with_limit(self, get_collection):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor

        collection = MagicMock()
        collection.find.return_value = cursor
        get_collection.return_value = collection

        filters = {"some_filter": "some_filter_value"}
        limit = 5

        result = get_payment_list(filters, limit=limit)

        self.assertEqual(result, cursor)
        collection.find.assert_called_once_with(filters)
        cursor.sort.assert_called_once_with("createdAt", DESCENDING)
        cursor.limit.assert_called_once_with(limit)

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_list_with_page(self, get_collection):
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.skip.return_value = cursor

        collection = MagicMock()
        collection.find.return_value = cursor
        get_collection.return_value = collection

        filters = {"some_filter": "some_filter_value"}
        limit = 5
        page = 10

        result = get_payment_list(filters, limit=limit, page=page)

        self.assertEqual(result, cursor)
        collection.find.assert_called_once_with(filters)
        cursor.sort.assert_called_once_with("createdAt", DESCENDING)
        cursor.limit.assert_called_once_with(limit)
        cursor.skip.assert_called_once_with(45)

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_item(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        uid = 'test_uid'

        result = get_payment_item(uid)

        self.assertEqual(result, collection.find_one.return_value)
        collection.find_one.assert_called_once_with({"_id": uid})

    @patch("payments.results_db.datetime")
    @patch("payments.results_db.get_mongodb_collection")
    def test_push_payment_message(self, get_collection, datetime):
        collection = MagicMock()
        get_collection.return_value = collection

        fake_datetime = "test_datetime"
        datetime.utcnow.return_value = fake_datetime

        data = {
            "description": "test_description",
            "amount": "test_amount",
            "currency": "test_currency",
            "date_oper": "test_date_oper",
            "type": "test_type",
            "source": "test_source",
            "account": "test_account",
            "okpo": "test_okpo",
            "mfo": "test_mfo",
            "name": "test_name"
        }
        message = 'Test message'
        message_id = 'TEST_MESSAGE_ID'

        result = push_payment_message(data, message_id, message)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(
            ANY,
            {
                '$push': {
                    'messages': {
                        "message_id": message_id,
                        "message": message,
                        "createdAt": fake_datetime
                    }
                }
            })

    @patch("payments.results_db.datetime")
    @patch("payments.results_db.get_mongodb_collection")
    def test_save_payment_item(self, get_collection, datetime):
        collection = MagicMock()
        get_collection.return_value = collection

        fake_datetime = "test_datetime"
        datetime.utcnow.return_value = fake_datetime

        data = {
            "description": "test_description",
            "amount": "test_amount",
            "currency": "test_currency",
            "date_oper": "test_date_oper",
            "type": "test_type",
            "source": "test_source",
            "account": "test_account",
            "okpo": "test_okpo",
            "mfo": "test_mfo",
            "name": "test_name"
        }
        user = 'test_user'

        result = save_payment_item(data, user)

        self.assertEqual(result, collection.insert_one.return_value)
        collection.insert_one.assert_called_once_with({
            "_id": data_to_uid(data),
            "payment": data,
            "user": user,
            "createdAt": fake_datetime
        })

    @patch("payments.results_db.get_mongodb_collection")
    def test_save_payment_item_duplicate(self, get_collection):
        collection = MagicMock()
        collection.insert_one.side_effect = DuplicateKeyError('error')
        get_collection.return_value = collection

        data = {'test_field': 'test_value'}
        user = 'test_user'

        result = save_payment_item(data, user)

        self.assertEqual(result, None)

    @patch("payments.results_db.get_mongodb_collection")
    def test_set_payment_params(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        data = {
            "description": "test_description",
            "amount": "test_amount",
            "currency": "test_currency",
            "date_oper": "test_date_oper",
            "type": "test_type",
            "source": "test_source",
            "account": "test_account",
            "okpo": "test_okpo",
            "mfo": "test_mfo",
            "name": "test_name"
        }
        params = {'test_param': 'test_value'}

        result = set_payment_params(data, params)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(
            ANY, {'$set': {'params': params}}
        )

    @patch("payments.results_db.get_mongodb_collection")
    def test_set_payment_resolution(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        data = {
            "description": "test_description",
            "amount": "test_amount",
            "currency": "test_currency",
            "date_oper": "test_date_oper",
            "type": "test_type",
            "source": "test_source",
            "account": "test_account",
            "okpo": "test_okpo",
            "mfo": "test_mfo",
            "name": "test_name"
        }
        params = {'test_param': 'test_value'}

        result = set_payment_resolution(data, params)

        self.assertEqual(result, collection.update_one.return_value)
        collection.update_one.assert_called_once_with(
            ANY, {'$set': {'resolution': params}}
        )

    @patch("payments.results_db.get_mongodb_collection")
    def test_get_payment_item_by_params(self, get_collection):
        collection = MagicMock()
        get_collection.return_value = collection

        params = {'test_param': 'test_value'}

        result = get_payment_item_by_params(params)

        self.assertEqual(result, collection.find_one.return_value)
        collection.find_one.assert_called_once_with(
            {"$and": [{"params": params}]}
        )
