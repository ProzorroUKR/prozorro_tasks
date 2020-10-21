from environment_settings import API_SIGN_HOST, API_SIGN_USER, API_SIGN_PASSWORD, TIMEZONE
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from datetime import datetime
from fiscal_bot.tasks import prepare_receipt_request, send_request_receipt
from celery.exceptions import Retry
from unittest.mock import patch, Mock
import requests
import unittest
import base64


@patch('celery_worker.locks.get_mongodb_collection', Mock(return_value=Mock(find_one=Mock(return_value=None))))
class ReceiptTestCase(unittest.TestCase):

    @patch("fiscal_bot.tasks.prepare_receipt_request.retry")
    @patch("fiscal_bot.tasks.build_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_prepare_request_exception(self, requests_mock, build_receipt_request_mock, retry_mock):
        retry_mock.side_effect = Retry
        build_receipt_request_mock.return_value = "file.xml", b"contents"

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
            lot_index=None,
        )

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")
        with self.assertRaises(Retry):
            prepare_receipt_request(supplier=supplier)

        retry_mock.assert_called_once_with(
            exc=requests_mock.post.side_effect
        )

    @patch("fiscal_bot.tasks.prepare_receipt_request.retry")
    @patch("fiscal_bot.tasks.build_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_prepare_request_error(self, requests_mock, build_receipt_request_mock, retry_mock):
        retry_mock.side_effect = Retry
        build_receipt_request_mock.return_value = "file.xml", b"contents"
        requests_mock.post.return_value = Mock(
            status_code=502,
            text="Bad Gateway",
            headers={"Retry-After": 12}
        )
        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
            lot_index=None,
        )

        with self.assertRaises(Retry):
            prepare_receipt_request(supplier=supplier)

        retry_mock.assert_called_once_with(
            countdown=12
        )

    @patch("fiscal_bot.tasks.send_request_receipt")
    @patch("fiscal_bot.tasks.build_receipt_request")
    def test_prepare_request_success(self, build_receipt_mock, send_request_receipt_mock):
        build_receipt_mock.return_value = "hallo.xml", b"unencrypted contents"

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
            lot_index=None,
        )

        with patch("fiscal_bot.tasks.get_now") as get_now_mock:
            get_now_mock.return_value = TIMEZONE.localize(datetime(2019, 4, 1, 16, 1))  # Monday 16:01

            with patch("fiscal_bot.tasks.requests") as requests_mock:
                requests_mock.post.side_effect = [
                    Mock(
                        status_code=200,
                        content=b"content",
                    ),
                ]
                prepare_receipt_request(supplier=supplier)

            requests_mock.post.assert_called_once_with(
                "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
                files={'file': ("hallo.xml", b"unencrypted contents")},
                auth=(API_SIGN_USER, API_SIGN_PASSWORD),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            send_request_receipt_mock.apply_async.assert_called_once_with(
                kwargs=dict(
                    prepare_receipt_request_task=prepare_receipt_request,
                    request_data=base64.b64encode(b"content").decode(),
                    filename="hallo.xml",
                    supplier=supplier,
                    requests_reties=0
                )
            )


    @patch("fiscal_bot.tasks.build_receipt_request")
    def test_prepare_request_call_next_task(self, build_receipt_mock):
        build_receipt_mock.return_value = "hallo.xml", b"unencrypted contents"

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
            lot_index=None,
        )

        with patch("fiscal_bot.tasks.get_now") as get_now_mock:
            get_now_mock.return_value = TIMEZONE.localize(datetime(2019, 4, 1, 16, 1))  # Monday 16:01

            with patch("fiscal_bot.tasks.requests") as requests_mock:
                requests_mock.post.side_effect = [
                    Mock(
                        status_code=200,
                        content=b"content",
                    ),
                ]
                prepare_receipt_request(supplier=supplier)

            requests_mock.post.assert_called_once_with(
                "{}/encrypt_fiscal/file".format(API_SIGN_HOST),
                files={'file': ("hallo.xml", b"unencrypted contents")},
                auth=(API_SIGN_USER, API_SIGN_PASSWORD),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            res = send_request_receipt.apply_async(
                kwargs=dict(
                    prepare_receipt_request_task=prepare_receipt_request,
                    request_data=base64.b64encode(b"content").decode(),
                    filename="hallo.xml",
                    supplier=supplier,
                    requests_reties=0
                )
            )
            self.assertIsNotNone(res)

    @patch("fiscal_bot.tasks.send_request_receipt")
    @patch("fiscal_bot.tasks.build_receipt_request")
    def test_lot_index_change_backward_compatibility(self, build_receipt_mock, send_request_receipt_mock):
        build_receipt_mock.return_value = "hallo.xml", b"unencrypted contents"

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )

        with patch("fiscal_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = [
                Mock(
                    status_code=200,
                    content=b"content",
                ),
            ]
            prepare_receipt_request(supplier=supplier)

        build_receipt_mock.assert_called_once_with(
            prepare_receipt_request, supplier["tenderID"], None, supplier["identifier"], supplier["name"]
        )

