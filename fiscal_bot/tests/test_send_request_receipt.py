from environment_settings import TIMEZONE, FISCAL_API_HOST
from datetime import datetime, timedelta
from fiscal_bot.tasks import send_request_receipt
from celery.exceptions import Retry
from unittest.mock import patch, Mock
import requests
import unittest


class ReceiptTestCase(unittest.TestCase):

    @patch("fiscal_bot.tasks.get_task_result")
    @patch("fiscal_bot.tasks.send_request_receipt.retry")
    @patch("fiscal_bot.tasks.requests")
    def test_request_exception(self, requests_mock, retry_mock, get_result_mock):
        get_result_mock.return_value = None
        retry_mock.side_effect = Retry
        filename = "test.xml"
        request_data = "Y29udGVudA=="

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )

        requests_mock.post.side_effect = requests.exceptions.ConnectionError("You shall not pass!")

        with self.assertRaises(Retry):
            send_request_receipt(
                request_data=request_data, filename=filename,
                supplier=supplier, requests_reties=0
            )

        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)

    @patch("fiscal_bot.tasks.get_task_result")
    @patch("fiscal_bot.tasks.send_request_receipt.retry")
    @patch("fiscal_bot.tasks.requests")
    def test_request_error_status(self, requests_mock, retry_mock, get_result_mock):
        get_result_mock.return_value = None
        retry_mock.side_effect = Retry
        filename = "test.xml"
        request_data = "Y29udGVudA=="

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )

        requests_mock.post.return_value = Mock(
            status_code=500,
            text="Bad Gateway",
            headers={"Retry-After": 13}
        )
        with self.assertRaises(Retry):
            send_request_receipt(
                request_data=request_data, filename=filename,
                supplier=supplier, requests_reties=0
            )

        retry_mock.assert_called_once_with(countdown=13)

    @patch("fiscal_bot.tasks.get_task_result")
    @patch("fiscal_bot.tasks.prepare_check_request")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    def test_request_error_response(self, requests_mock, save_sfs_data_mock,
                                            check_request_mock, get_result_mock):
        get_result_mock.return_value = None
        filename = "test.xml"
        request_data = "Y29udGVudA=="

        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )
        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: {"status": "ERROR"}
        )

        send_request_receipt(
            request_data=request_data, filename=filename,
            supplier=supplier, requests_reties=0
        )
        save_sfs_data_mock.apply_async.assert_not_called()
        check_request_mock.apply_async.assert_not_called()

    @patch("fiscal_bot.tasks.save_task_result")
    @patch("fiscal_bot.tasks.get_task_result")
    @patch("fiscal_bot.tasks.prepare_check_request")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    def test_request_success(self, decode_and_save_mock, prepare_check_request_mock,
                                     get_result_mock, save_result_mock):
        get_result_mock.return_value = None
        filename = "test.xml"
        request_data = "whatever"
        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )
        fiscal_response = {
            "id": "fa" * 16,
            "status": "OK",
            "kvt1Fname": "Response.xml",
            "kvt1Base64": "Y29udGVudA==",
        }

        with patch("fiscal_bot.tasks.get_now") as get_now_mock:
            get_now_mock.return_value = TIMEZONE.localize(datetime(2019, 3, 28, 16))

            with patch("fiscal_bot.tasks.requests") as requests_mock:
                requests_mock.post.side_effect = [
                    Mock(
                        status_code=200,
                        json=lambda: fiscal_response,
                    ),
                ]
                send_request_receipt(
                    request_data=request_data, filename=filename,
                    supplier=supplier, requests_reties=1
                )

        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/report'.format(FISCAL_API_HOST),
            json=[{'contentBase64': request_data, 'fname': filename}]
        )
        get_result_mock.assert_called_once_with(
            send_request_receipt,
            (supplier, 1)
        )
        save_result_mock.assert_called_once_with(
            send_request_receipt,
            fiscal_response,
            (supplier, 1)
        )
        decode_and_save_mock.apply_async.assert_called_once_with(
            kwargs=dict(
                name="Response.xml",
                data="Y29udGVudA==",
                tender_id=supplier["tender_id"],
                award_id=supplier["award_id"],
            )
        )

        prepare_check_request_mock.apply_async.assert_called_once_with(
            eta=TIMEZONE.localize(datetime(2019, 3, 29, 9)),
            kwargs=dict(
                uid="fa" * 16,
                supplier=supplier,
                request_time=get_now_mock.return_value,
                requests_reties=1,
            )
        )

    @patch("fiscal_bot.tasks.save_task_result")
    @patch("fiscal_bot.tasks.get_task_result")
    @patch("fiscal_bot.tasks.prepare_check_request")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    def test_saved_request_success(self, decode_and_save_mock, prepare_check_request_mock,
                                   get_result_mock, save_result_mock):
        filename = "test.xml"
        request_data = "whatever"
        supplier = dict(
            name="Python Monty Иванович",
            identifier="AA426097",
            tender_id="f" * 32,
            award_id="c" * 32,
            tenderID="UA-2019-01-31-000147-a",
        )
        fiscal_response = {
            "id": "fa" * 16,
            "status": "OK",
            "kvt1Fname": "Response.xml",
            "kvt1Base64": "Y29udGVudA==",
        }
        get_result_mock.return_value = fiscal_response

        with patch("fiscal_bot.tasks.get_now") as get_now_mock:
            get_now_mock.return_value = TIMEZONE.localize(datetime(2019, 3, 28, 12))

            with patch("fiscal_bot.tasks.requests") as requests_mock:
                send_request_receipt(
                    request_data=request_data, filename=filename,
                    supplier=supplier, requests_reties=1
                )

        get_result_mock.assert_called_once_with(
            send_request_receipt,
            (supplier, 1)
        )
        requests_mock.post.assert_not_called()
        save_result_mock.assert_not_called()
        decode_and_save_mock.apply_async.assert_called_once_with(
            kwargs=dict(
                name="Response.xml",
                data="Y29udGVudA==",
                tender_id=supplier["tender_id"],
                award_id=supplier["award_id"],
            )
        )
        prepare_check_request_mock.apply_async.assert_called_once_with(
            eta=get_now_mock.return_value + timedelta(hours=1),
            kwargs=dict(
                uid="fa" * 16,
                supplier=supplier,
                request_time=get_now_mock.return_value,
                requests_reties=1,
            )
        )
