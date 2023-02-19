from environment_settings import (
    API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD, CONNECT_TIMEOUT,
    READ_TIMEOUT,
)
from nazk_bot.tasks import prepare_nazk_request
from celery.exceptions import Retry
from unittest.mock import patch, Mock
import requests
import unittest
import base64


@patch('celery_worker.locks.get_mongodb_collection', Mock(return_value=Mock(find_one=Mock(return_value=None))))
class ReceiptTestCase(unittest.TestCase):

    @patch("nazk_bot.tasks.prepare_nazk_request.retry")
    @patch("nazk_bot.tasks.requests")
    def test_prepare_request_exception(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry

        data = dict(
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "1"*10,
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
        )

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")
        with self.assertRaises(Retry):
            prepare_nazk_request(**data)

        retry_mock.assert_called_once_with(
            exc=requests_mock.post.side_effect
        )

    @patch("nazk_bot.tasks.prepare_nazk_request.retry")
    @patch("nazk_bot.tasks.requests")
    def test_prepare_request_error(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        requests_mock.post.return_value = Mock(
            status_code=502,
            text="Bad Gateway",
            headers={"Retry-After": 12}
        )
        data = dict(
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "1" * 10,
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
        )

        with self.assertRaises(Retry):
            prepare_nazk_request(**data)

        retry_mock.assert_called_once_with(
            countdown=12
        )

    @patch("nazk_bot.tasks.send_request_nazk")
    def test_prepare_request_success(self, send_request_nazk_mock):

        code_id = "1" * 10
        legal_name = "Wow"
        supplier = {
            "identifier": {
                "scheme": "UA-EDR",
                "legalName": legal_name,
                "id": code_id,
            },
        }
        tender_id = "f" * 32
        award_id = "c" * 32
        data = dict(
            supplier=supplier,
            tender_id=tender_id,
            award_id=award_id,
        )

        with patch("nazk_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = [
                Mock(
                    status_code=200,
                    content=b"content",
                ),
            ]
            prepare_nazk_request(**data)

        data = {"entityType": "individual", "entityRegCode": code_id, "indLastName": legal_name,
                "indFirstName": "", "indPatronymic": ""}
        requests_mock.post.assert_called_once_with(
            "{}/encrypt_nazk_data".format(API_SIGN_HOST),
            json=data,
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={'User-agent': 'prozorro_tasks'},
        )

        send_request_nazk_mock.apply_async.assert_called_once_with(
            kwargs=dict(
                request_data=b"content",
                supplier=supplier,
                tender_id=tender_id,
                award_id=award_id,
                requests_reties=0
            )
        )
