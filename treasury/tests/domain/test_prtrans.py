import datetime
import requests
from dateutil.tz import tzoffset
from app.tests.base import BaseTestCase
from unittest.mock import patch, MagicMock, Mock, call
from celery_worker.celery import app
from celery.exceptions import Retry
from treasury.domain.prtrans import save_transaction_xml
from treasury.domain.prtrans import put_transaction, ds_upload, attach_doc_to_transaction
from treasury.exceptions import DocumentServiceForbiddenError, DocumentServiceError, ApiServiceError
from treasury.settings import PUT_TRANSACTION_SUCCESSFUL_STATUS, ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS


@app.task
def _mock_task(self):
    pass


class TestCase(BaseTestCase):
    @patch("treasury.domain.prtrans.ds_upload")
    def test_save_transaction_xml(self, ds_upload_mock):
        ds_upload_mock.return_value = {
            "url": "http://whatever",
        }
        source = b"abc"
        transactions_ids = ["1234567AA"]
        save_transaction_xml(_mock_task, transactions_ids, source)
        ds_upload_mock.assert_called_once_with(
            _mock_task,
            file_content=source,
            file_name='Transaction_1234567AA.xml'
        )

    @patch("treasury.domain.prtrans.ds_upload")
    def test_save_transaction_xml_several_ids(self, ds_upload_mock):
        ds_upload_mock.return_value = {
            "url": "http://whatever",
        }
        source = b"abc"
        transactions_ids = ['LL123', 'SSS222', 'GGG333', 'NNN444']
        save_transaction_xml(_mock_task, transactions_ids, source)
        ds_upload_mock.assert_called_once_with(
            _mock_task,
            file_content=source,
            file_name='Transaction_LL123_and_3_others.xml'
        )

    @patch('requests.Session')
    def test_put_transaction(self, mock_session):

        mock_get_response_class = type(
            "GetResponse", (object,),
            {"status_code": 400, "text": "get_response_text", "cookies": {"SERVER_ID": "123_ID"}},
        )

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

        mock_session.return_value.get.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(ApiServiceError):
            put_transaction(transaction)

        mock_session.return_value.get.side_effect = None
        mock_session.return_value.get.return_value = mock_get_response_class

        result = put_transaction(transaction)
        self.assertEqual(result, (400, {"SERVER_ID": "123_ID"}))

        mock_get_response_class.status_code = 200

        mock_put_response = type(
            "PutResponse", (object,),
            {"status_code": 422, "text": "put_response_text", "cookies": {"SERVER_ID": "123_ID"}}
        )
        mock_session.return_value.put.return_value = mock_put_response

        result = put_transaction(transaction)
        self.assertEqual(result, (422, {"SERVER_ID": "123_ID"}))

        mock_put_response.status_code = 301
        result = put_transaction(transaction)
        self.assertEqual(result, (301, {"SERVER_ID": "123_ID"}))

        mock_put_response.status_code = 201
        result = put_transaction(transaction)
        self.assertEqual(result, (PUT_TRANSACTION_SUCCESSFUL_STATUS, {"SERVER_ID": "123_ID"}))

    @patch('requests.Session')
    def test_ds_upload(self, mock):

        def get_json(self):
            return self.json_data

        mock_response_class = type(
            "MockResponse", (object,),
            {"status_code": 200, "json_data": "some_success_response", "text": "response_text", "json": get_json}
        )

        mock.return_value.post.return_value = mock_response_class()
        result = ds_upload(_mock_task, 'transaction.xml', b'abc')
        self.assertEqual(result, 'some_success_response')

        mock_response_class.status_code = 403
        with self.assertRaises(Retry):
            ds_upload(_mock_task, 'transaction.xml', b'abc')

        mock_response_class.status_code = 400
        with self.assertRaises(Retry):
            ds_upload(_mock_task, 'transaction.xml', b'abc')

        mock_response_class.side_effect = requests.exceptions.ConnectionError()
        with self.assertRaises(Retry):
            ds_upload(_mock_task, 'transaction.xml', b'abc')
        mock_response_class.side_effect = None

    @patch('requests.Session')
    def test_attach_doc_to_transaction(self, mock_session):
        mock_get_response_class = type(
            "GetResponse", (object,),
            {"status_code": 400, "text": "get_response_text", "cookies": {"SERVER_ID": "123_ID"}}
        )

        data = {'data': 'abc', 'title': 'title123'}
        contract_id = 'AA12345'
        transaction_id = '23456667'

        mock_session.return_value.get.side_effect = requests.exceptions.ConnectionError()

        _cookies = {"SERVER_ID": "123_ID"}
        with self.assertRaises(ApiServiceError):
            attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)

        mock_session.return_value.get.side_effect = None
        mock_session.return_value.get.return_value = mock_get_response_class

        result = attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)
        self.assertEqual(result, 400)

        mock_get_response_class.status_code = 200
        mock_post_response_class = type(
            "PostResponse", (object,),
            {"status_code": 201, "text": "get_response_text", "cookies": {"SERVER_ID": "123_ID"}}
        )
        mock_session.return_value.post.return_value = mock_post_response_class

        result = attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)
        self.assertEqual(result, ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS)

        mock_get_response_class.status_code = 422
        result = attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)
        self.assertEqual(result, 422)

        mock_get_response_class.status_code = 403
        result = attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)
        self.assertEqual(result, 403)

        mock_get_response_class.status_code = 301
        result = attach_doc_to_transaction(data, contract_id, transaction_id, _cookies)
        self.assertEqual(result, 301)
