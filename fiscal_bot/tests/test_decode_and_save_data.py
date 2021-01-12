from environment_settings import API_SIGN_USER, API_SIGN_HOST, API_SIGN_PASSWORD, CONNECT_TIMEOUT, READ_TIMEOUT
from fiscal_bot.tasks import decode_and_save_data
from fiscal_bot.settings import DOC_TYPE
from celery.exceptions import Retry
from unittest.mock import patch, MagicMock
import base64
import unittest
import requests


class DecodeAndSaveTestCase(unittest.TestCase):

    @patch("fiscal_bot.tasks.decode_and_save_data.retry")
    @patch("fiscal_bot.tasks.requests")
    def test_connection_error(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        tender_id = "a" * 32
        award_id = "f" * 32
        name = "26591010101017J1603101100000000111220172659.KVT"
        data = "aGVsbG8="

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        with self.assertRaises(Retry):
            decode_and_save_data(name, data, tender_id, award_id)

        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)

    @patch("fiscal_bot.tasks.upload_to_doc_service")
    @patch("fiscal_bot.tasks.decode_and_save_data.retry")
    def test_422_error(self, retry_mock, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        name = "26591010101017J1603101100000000111220172659.KVT"
        data = "aGVsbG8="

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(status_code=422, text="Unexpected smt", headers={})
            decode_and_save_data(name, data, tender_id, award_id)

        retry_mock.assert_not_called()
        upload_to_doc_service_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.decode_and_save_data.retry")
    @patch("fiscal_bot.tasks.requests")
    def test_500_error(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        tender_id = "a" * 32
        award_id = "f" * 32
        name = "26591010101017J1603101100000000111220172659.KVT"
        data = "aGVsbG8="

        requests_mock.post.return_value = MagicMock(
            status_code=500,
            text="Unexpected smt",
            headers={"Retry-After": 14}
        )

        with self.assertRaises(Retry):
            decode_and_save_data(name, data, tender_id, award_id)

        retry_mock.assert_called_once_with(countdown=14)

    @patch("fiscal_bot.tasks.upload_to_doc_service")
    def test_no_filename(self, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        data = b"<?xml>Hello"
        name = "26591010101017J1603101100000000111220172659.KVT"

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(status_code=200, content=data, headers={})

            decode_and_save_data(name, base64.b64encode(data), tender_id, award_id)

        requests_mock.post.assert_called_once_with(
            "{}/decrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (name, data)},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

        upload_to_doc_service_mock.delay.assert_called_once_with(
            item_name='award',
            item_id='f' * 32,
            content=base64.b64encode(data).decode(),
            name=name,
            doc_type=DOC_TYPE,
            tender_id='a' * 32
        )

    @patch("fiscal_bot.tasks.upload_to_doc_service")
    def test_success(self, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        data = b"<?xml>Hello"
        name = "26591010101017J1603101100000000111220172659.KVT"

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(
                status_code=200,
                content=data,
                headers={"content-disposition": "attachment; filename={}.p7s".format(name)},
            )

            decode_and_save_data(name, base64.b64encode(data), tender_id, award_id)

        requests_mock.post.assert_called_once_with(
            "{}/decrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (name, data)},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

        upload_to_doc_service_mock.delay.assert_called_once_with(
            item_name='award',
            item_id='f' * 32,
            content=base64.b64encode(data).decode(),
            name=name + ".p7s",
            doc_type=DOC_TYPE,
            tender_id='a' * 32
        )
