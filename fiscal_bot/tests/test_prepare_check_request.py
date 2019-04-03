from environment_settings import API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD, TIMEZONE
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from fiscal_bot.tasks import prepare_check_request
from celery.exceptions import Retry
from datetime import datetime
from unittest.mock import patch, Mock, call
import requests
import base64
import unittest


class CheckResponseTestCase(unittest.TestCase):

    @patch("fiscal_bot.tasks.prepare_check_request.retry")
    @patch("fiscal_bot.tasks.check_for_response_file")
    @patch("fiscal_bot.tasks.requests")
    def test_prepare_request_exception(self, requests_mock, check_for_response_file_mock, retry_mock):
        retry_mock.side_effect = Retry
        uid = 265970448191511
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        request_time = TIMEZONE.localize(datetime(2019, 3, 29, 15, 47))

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        with self.assertRaises(Retry):
            prepare_check_request(
                uid,
                supplier=supplier,
                request_time=request_time,
                requests_reties=0,
            )

        requests_mock.post.assert_called_once_with(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (str(uid), str(uid).encode())},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)
        check_for_response_file_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.prepare_check_request.retry")
    @patch("fiscal_bot.tasks.check_for_response_file")
    @patch("fiscal_bot.tasks.requests")
    def test_prepare_request_status_error(self, requests_mock, check_for_response_file_mock, retry_mock):
        retry_mock.side_effect = Retry
        uid = 265970448191511
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        request_time = TIMEZONE.localize(datetime(2019, 3, 29, 15, 47))

        requests_mock.post.return_value = Mock(
            status_code=500,
            text="Bad Gateway",
            headers={"Retry-After": 16}
        )

        with self.assertRaises(Retry):
            prepare_check_request(
                uid,
                supplier=supplier,
                request_time=request_time,
                requests_reties=0,
            )

        requests_mock.post.assert_called_once_with(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (str(uid), str(uid).encode())},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        retry_mock.assert_called_once_with(countdown=16)
        check_for_response_file_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.check_for_response_file")
    @patch("fiscal_bot.tasks.requests")
    def test_prepare_request_success(self, requests_mock, check_for_response_file_mock):
        uid = 265970448191511
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        encoded_content = b"Hello"
        request_time = TIMEZONE.localize(datetime(2019, 3, 29, 15, 47))

        requests_mock.post.return_value = Mock(
            status_code=200,
            content=encoded_content,
        )

        prepare_check_request(
            uid,
            supplier=supplier,
            request_time=request_time,
            requests_reties=0,
        )

        requests_mock.post.assert_called_once_with(
            "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
            files={'file': (str(uid), str(uid).encode())},
            auth=(API_SIGN_USER, API_SIGN_PASSWORD),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        check_for_response_file_mock.delay.assert_called_once_with(
            request_data=base64.b64encode(encoded_content).decode(),
            supplier=supplier,
            request_time=request_time,
            requests_reties=0,
        )

