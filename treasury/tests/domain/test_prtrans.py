import datetime
import asyncio
import requests
from asyncio import Future
from dateutil.tz import tzoffset
from app.tests.base import BaseTestCase
from unittest.mock import patch, MagicMock, Mock, call
from treasury.domain.prtrans import save_transaction_xml
from treasury.domain.prtrans import put_transaction, ds_upload, attach_doc_to_contract
from treasury.exceptions import DocumentServiceForbiddenError, DocumentServiceError, ApiServiceError


class TestCase(BaseTestCase):
    @patch("treasury.domain.prtrans.ds_upload")
    def test_save_transaction(self, ds_upload_mock):
        ds_upload_mock.return_value = {
            "url": "http://whatever",
        }
        source = b"abc"
        transactions_ids = ["1234567AA"]
        save_transaction_xml(transactions_ids, source)
        ds_upload_mock.assert_called_once_with(
            file_content=source,
            file_name='Transaction_1234567AA.xml'
        )

    @patch("treasury.domain.prtrans.ds_upload")
    def test_save_transaction_several_ids(self, ds_upload_mock):
        ds_upload_mock.return_value = {
            "url": "http://whatever",
        }
        source = b"abc"
        transactions_ids = ['LL123', 'SSS222', 'GGG333', 'NNN444']
        save_transaction_xml(transactions_ids, source)
        ds_upload_mock.assert_called_once_with(
            file_content=source,
            file_name='Transaction_LL123_and_3_others.xml'
        )

    @patch('aiohttp.ClientSession.put')
    @patch('aiohttp.ClientSession.get')
    def test_put_transaction(self, mock_get, mock_put):

        mock_get_response_class = type("GetResponse", (object,), {"status": 400, "text": "get_response_text"})

        transaction = {
            'ref': '1',
            'doc_sq': 18.44,
            'doc_datd': datetime.datetime(2020, 3, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
            'doc_nam_a': 'Test',
            'doc_iban_a': 'UA678201720355110002000080850',
            'doc_nam_b': 'Test',
            'doc_iban_b': 'UA098201720355179002000014715',
            'msrprd_date': datetime.datetime(2020, 3, 11, 0, 0, tzinfo=tzoffset(None, 7200)),
            'id_contract': '11C2E7D03AF649668BF9FFB1D0EF767D',
            'doc_status': -1
            }
        document = {
            'data': 'some_data_from_ds',
            'get_url': 'url_to_access_the_document'
        }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_get.return_value = Future()
        mock_get.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(ApiServiceError):
            coroutine = put_transaction(transaction, document)
            loop.run_until_complete(coroutine)

        mock_get.side_effect = None
        mock_get.return_value.set_result(mock_get_response_class)

        coroutine = put_transaction(transaction, document)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 400)

        mock_get_response_class.status = 200

        mock_put_response = type("PutResponse", (object,), {"status": 422, "text": "put_response_text"})
        mock_put.return_value = Future()
        mock_put.return_value.set_result(mock_put_response)

        coroutine = put_transaction(transaction, document)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 422)

        mock_put_response.status = 301
        coroutine = put_transaction(transaction, document)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 301)

        mock_put_response.status = 201
        coroutine = put_transaction(transaction, document)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, "Success")
        loop.close()

    @patch('requests.post')
    def test_ds_upload(self, mock):

        def get_json(self):
            return self.json_data

        mock_response_class = type(
            "MockResponse", (object,),
            {"status_code": 200, "json_data": "some_success_response", "json": get_json}
        )

        mock.return_value = mock_response_class()
        result = ds_upload('transaction.xml', b'abc')
        self.assertEqual(result, 'some_success_response')

        mock_response_class.status_code = 403
        with self.assertRaises(DocumentServiceForbiddenError):
            ds_upload('transaction.xml', b'abc')

        mock_response_class.status_code = 400
        with self.assertRaises(DocumentServiceError):
            ds_upload('transaction.xml', b'abc')

        mock_response_class.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(DocumentServiceError):
            ds_upload('transaction.xml', b'abc')
        mock_response_class.side_effect = None

    @patch('aiohttp.ClientSession.post')
    @patch('aiohttp.ClientSession.get')
    def test_attach_doc_to_contract(self, mock_get, mock_post):
        mock_get_response_class = type(
            "GetResponse", (object,), {"status": 400, "text": "get_response_text", "cookies": "some_cookies"})

        data = {'data': 'abc', 'title': 'title123'}
        contract_id = 'AA12345'
        transaction_id = '23456667'

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_get.return_value = Future()
        mock_get.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(ApiServiceError):
            coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
            loop.run_until_complete(coroutine)

        mock_get.side_effect = None
        mock_get.return_value.set_result(mock_get_response_class)

        coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 400)

        mock_get_response_class.status = 200
        mock_post_response_class = type("PostResponse", (object,), {"status": 201, "text": "get_response_text"})
        mock_post.return_value = Future()
        mock_post.return_value.set_result(mock_post_response_class)

        coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, mock_post_response_class)

        mock_get_response_class.status = 422
        coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 422)

        mock_get_response_class.status = 403
        coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 403)

        mock_get_response_class.status = 301
        coroutine = attach_doc_to_contract(data, contract_id, transaction_id)
        result = loop.run_until_complete(coroutine)
        self.assertEqual(result, 301)
        loop.close()