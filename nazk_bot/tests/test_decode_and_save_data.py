from environment_settings import API_SIGN_USER, API_SIGN_HOST, API_SIGN_PASSWORD, CONNECT_TIMEOUT, READ_TIMEOUT
from nazk_bot.tasks import decode_and_save_data
from nazk_bot.settings import DOC_TYPE, DOC_NAME
from celery.exceptions import Retry
from unittest.mock import patch, MagicMock
import base64
import unittest
import requests
import json


class DecodeAndSaveTestCase(unittest.TestCase):

    @patch("nazk_bot.tasks.decode_and_save_data.retry")
    @patch("nazk_bot.tasks.requests")
    def test_connection_error(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": 'Wow',
                "id": "AA426097",
            },
        }
        tender_id = "a" * 32
        award_id = "f" * 32
        data = "aGVsbG8="

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        with self.assertRaises(Retry):
            decode_and_save_data(data, supplier, tender_id, award_id)

        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)

    @patch("nazk_bot.tasks.upload_to_doc_service")
    @patch("nazk_bot.tasks.decode_and_save_data.retry")
    def test_422_error(self, retry_mock, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": 'Wow',
                "id": "AA426097",
            },
        }
        data = "aGVsbG8="

        with patch("nazk_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(status_code=422, text="Unexpected smt", headers={})
            decode_and_save_data(data, supplier, tender_id, award_id)

        retry_mock.assert_not_called()
        upload_to_doc_service_mock.delay.assert_not_called()

    @patch("nazk_bot.tasks.decode_and_save_data.retry")
    @patch("nazk_bot.tasks.requests")
    def test_500_error(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        tender_id = "a" * 32
        award_id = "f" * 32
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": 'Wow',
                "id": "AA426097",
            },
        }
        data = "aGVsbG8="

        requests_mock.post.return_value = MagicMock(
            status_code=500,
            text="Unexpected smt",
            headers={"Retry-After": 14}
        )

        with self.assertRaises(Retry):
            decode_and_save_data(data, supplier, tender_id, award_id)

        retry_mock.assert_called_once_with(countdown=14)

    @patch("nazk_bot.tasks.upload_to_doc_service")
    def test_no_filename(self, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": 'Wow',
                "id": "AA426097",
            },
        }
        data = b'{"answer": "data"}'
        data_enc = base64.b64encode(data)

        with patch("nazk_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(status_code=200, content=data, headers={})

            decode_and_save_data(data_enc, supplier, tender_id, award_id)

        requests_mock.post.assert_called_once_with(
            url="{}/decrypt_nazk_data".format(API_SIGN_HOST),
            json={"data": data_enc},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'User-agent': 'prozorro_tasks'},
        )

        upload_to_doc_service_mock.delay.assert_called_once_with(
            item_name='award',
            item_id='f' * 32,
            content=data,
            name=DOC_NAME,
            doc_type=DOC_TYPE,
            tender_id='a' * 32,
            decode_data=False,
        )

    @patch("nazk_bot.tasks.upload_to_doc_service")
    def test_success(self, upload_to_doc_service_mock):
        tender_id = "a" * 32
        award_id = "f" * 32
        data = b'{"answer": "data"}'
        data_enc = base64.b64encode(data)
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": 'Wow',
                "id": "AA426097",
            },
        }

        with patch("nazk_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = MagicMock(
                status_code=200,
                content=data,
                headers={
                    "User-agent": "prozorro_tasks",
                },
            )

            decode_and_save_data(base64.b64encode(data), supplier, tender_id, award_id)

        requests_mock.post.assert_called_once_with(
            url="{}/decrypt_nazk_data".format(API_SIGN_HOST),
            json={"data": data_enc},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'User-agent': 'prozorro_tasks'},
        )

        upload_to_doc_service_mock.delay.assert_called_once_with(
            item_name='award',
            item_id='f' * 32,
            content=data,
            name=DOC_NAME,
            doc_type=DOC_TYPE,
            tender_id='a' * 32,
            decode_data=False
        )
