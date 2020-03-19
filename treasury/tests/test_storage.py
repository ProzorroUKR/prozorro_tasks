from treasury.storage import get_collection, init_organisations_index, ORG_UNIQUE_FIELD, \
    get_contract_context, save_contract_context, update_organisations, get_organisation
from environment_settings import TREASURY_DB_NAME, TREASURY_ORG_COLLECTION
from pymongo import UpdateOne, DeleteMany
from pymongo.errors import PyMongoError
from celery.exceptions import Retry
from unittest.mock import patch, Mock
import unittest


class StorageTestCase(unittest.TestCase):

    @patch("treasury.storage.get_mongodb_collection")
    def test_get_collection(self, get_mongodb_collection_mock):
        get_mongodb_collection_mock.return_value = {"beep"}
        result = get_collection(collection_name="cats")

        get_mongodb_collection_mock.assert_called_once_with(
            collection_name="cats",
            db_name=TREASURY_DB_NAME
        )
        self.assertEqual(
            result,
            get_mongodb_collection_mock.return_value
        )

    @patch("treasury.storage.get_collection")
    def test_init_organisations_index(self, get_collection_mock):
        get_collection_mock.return_value.create_index.side_effect = PyMongoError("Connection error")

        with self.assertRaises(Retry):
            init_organisations_index()

        get_collection_mock.assert_called_once_with(TREASURY_ORG_COLLECTION)
        get_collection_mock.return_value.create_index.assert_called_once_with(ORG_UNIQUE_FIELD)

    @patch("treasury.storage.get_collection")
    def test_get_contract_context(self, get_collection_mock):
        uid = "123"
        task = Mock()
        context = ["ja ja"]
        get_collection_mock.return_value.find_one.return_value = {"context": context}

        result = get_contract_context(task, uid)

        get_collection_mock.assert_called_once_with()
        get_collection_mock.return_value.find_one.assert_called_once_with({"_id": uid})
        self.assertEqual(result, context)

    @patch("treasury.storage.get_collection")
    def test_get_contract_context_error(self, get_collection_mock):
        uid = "123"
        task = Mock(retry=Retry)
        get_collection_mock.return_value.find_one.side_effect = PyMongoError("Connection error")

        with self.assertRaises(Retry):
            get_contract_context(task, uid)

    @patch("treasury.storage.get_collection")
    def test_save_contract_context(self, get_collection_mock):
        uid = "123"
        task = Mock()
        data = ["ja ja"]

        save_contract_context(task, uid, data)

        get_collection_mock.assert_called_once_with()
        get_collection_mock.return_value.update_one.assert_called_once_with(
            {"_id": uid},
            {"$set": {"context": data}},
            upsert=True
        )

    @patch("treasury.storage.get_collection")
    def test_save_contract_context_error(self, get_collection_mock):
        uid = "123"
        task = Mock(retry=Retry)
        data = ["ja ja"]
        get_collection_mock.return_value.update_one.side_effect = PyMongoError("Connection error")

        with self.assertRaises(Retry):
            save_contract_context(task, uid, data)

    @patch("treasury.storage.get_collection")
    def test_update_organisations(self, get_collection_mock):
        task = Mock()
        records = [
            {
                ORG_UNIQUE_FIELD: "1",
                "text": "data"
            },
            {
                ORG_UNIQUE_FIELD: "12",
                "text": "data data"
            }
        ]

        update_organisations(task, records)

        get_collection_mock.assert_called_once_with(collection_name=TREASURY_ORG_COLLECTION)
        get_collection_mock.return_value.bulk_write.assert_called_once_with(
            [
                UpdateOne({ORG_UNIQUE_FIELD: "1"}, {"$set": records[0]}, upsert=True),
                UpdateOne({ORG_UNIQUE_FIELD: "12"}, {"$set": records[1]}, upsert=True),
                DeleteMany({'edrpou_code': {'$nin': ['1', '12']}})
            ]
        )

    @patch("treasury.storage.get_collection")
    def test_update_organisations_error(self, get_collection_mock):
        get_collection_mock.return_value.bulk_write.side_effect = PyMongoError("Connection error")
        task = Mock(retry=Retry)
        records = []

        with self.assertRaises(Retry):
            update_organisations(task, records)

    @patch("treasury.storage.get_collection")
    def test_get_organisation(self, get_collection_mock):
        uid = "123"
        task = Mock()
        org = {"code": uid}
        get_collection_mock.return_value.find_one.return_value = org

        result = get_organisation(task, uid)
        self.assertEqual(result, org)
        get_collection_mock.return_value.find_one.assert_called_once_with({"edrpou_code": uid})

    @patch("treasury.storage.get_collection")
    def test_get_organisation_error(self, get_collection_mock):
        uid = "123"
        task = Mock(retry=Retry)
        get_collection_mock.return_value.find_one.side_effect = PyMongoError("Connection error")

        with self.assertRaises(Retry):
            get_organisation(task, uid)
