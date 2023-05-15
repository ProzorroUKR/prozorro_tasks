from environment_settings import TIMEZONE, NAZK_API_HOST, NAZK_API_INFO_URI
from datetime import datetime, timedelta
from nazk_bot.tasks import send_request_nazk
from tasks_utils.settings import DEFAULT_HEADERS
from celery.exceptions import Retry
from unittest.mock import patch, Mock
import requests
import unittest


class NazkTestCase(unittest.TestCase):

    @patch("nazk_bot.tasks.send_request_nazk.retry")
    @patch("nazk_bot.tasks.requests")
    def test_request_exception(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        filename = "test.xml"
        request_data = "Y29udGVudA=="

        data = dict(
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "AA426097",
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
        )

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        with self.assertRaises(Retry):
            send_request_nazk(
                **data, requests_reties=0
            )

        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect, countdown=5)

    retry_count_to_timeout_in_sec_test_cases = [
        {"attempt": 0, "timeout": 5},
        {"attempt": 1, "timeout": 10},
        {"attempt": 10, "timeout": 3600},
    ]

    @patch("nazk_bot.tasks.send_request_nazk.request_stack")
    @patch("nazk_bot.tasks.send_request_nazk.retry")
    @patch("nazk_bot.tasks.requests")
    def test_request_exception(self, requests_mock, retry_mock, task_request_mock):
        retry_mock.side_effect = Retry
        request_data = "Y29udGVudA=="

        data = dict(
            request_data=request_data,
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "AA426097",
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
            requests_reties=0
        )

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        for test_case in self.retry_count_to_timeout_in_sec_test_cases:
            attempt_count = test_case["attempt"]
            timeout_in_sec = test_case["timeout"]
            with self.subTest():
                task_request_mock.top = Mock(retries=attempt_count)
                with self.assertRaises(Retry):

                    send_request_nazk(**data)

                retry_mock.assert_called_with(
                    exc=requests_mock.post.side_effect,
                    countdown=timeout_in_sec
                )

    @patch("nazk_bot.tasks.send_request_nazk.retry")
    @patch("nazk_bot.tasks.requests")
    def test_request_error_status(self, requests_mock, retry_mock):
        retry_mock.side_effect = Retry
        request_data = "Y29udGVudA=="

        data = dict(
            request_data=request_data,
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "AA426097",
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
            requests_reties=0
        )

        requests_mock.post.return_value = Mock(
            status_code=500,
            text="Bad Gateway",
            headers={"Retry-After": 13}
        )
        with self.assertRaises(Retry):
            send_request_nazk(**data)

        retry_mock.assert_called_once_with(countdown=13)

    @patch("nazk_bot.tasks.get_cert_base64")
    @patch("nazk_bot.tasks.decode_and_save_data")
    def test_request_success(self, decode_and_save_mock, get_open_cert_mock):
        request_data = "whatever"
        data = dict(
            request_data=request_data,
            supplier={
                "identifier": {
                    "scheme": "UA-EDR",
                    "legalName": 'Wow',
                    "id": "AA426097",
                },
            },
            tender_id="f" * 32,
            award_id="c" * 32,
            requests_reties=1
        )

        response = {
            "id": "fa" * 16,
            "status": "OK",
            "kvt1Fname": "Response.xml",
            "kvt1Base64": "Y29udGVudA==",
        }

        cert = "Y29udGVudA=="
        get_open_cert_mock.return_value = cert

        with patch("nazk_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = [
                Mock(
                    status_code=200,
                    text=response,
                ),
            ]
            send_request_nazk(**data)

        requests_mock.post.assert_called_once_with(
            url="{host}/{uri}".format(host=NAZK_API_HOST, uri=NAZK_API_INFO_URI),
            json={"certificate": cert, "data": request_data},
            headers=DEFAULT_HEADERS,
        )

        decode_and_save_mock.apply_async.assert_called_once_with(
            kwargs=dict(
                data=response,
                supplier=data["supplier"],
                tender_id=data["tender_id"],
                award_id=data["award_id"],
            )
        )
