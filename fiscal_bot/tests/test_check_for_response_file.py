from environment_settings import FISCAL_API_HOST, TIMEZONE, FISCAL_API_PROXIES
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from fiscal_bot.tasks import check_for_response_file
from fiscal_bot.settings import REQUEST_MAX_RETRIES, CUSTOM_WORK_DAY
from celery.exceptions import Retry
from datetime import datetime
from unittest.mock import patch, Mock, call
import requests
import unittest


class CheckResponseTestCase(unittest.TestCase):
    fail_response = {
        'message': None,
        'status': 'OK',
        'id': None,
        'kvt1Base64': None,
        'kvt1Fname': None,
        'kvtList': [
            {
                'kvtBase64': '',
                'kvtFname': '26591010101017J1499101100000000311220182659.KVT',
                'numKvt': 1,
                'finalKvt': 0,
                'status': 1
            }
        ]
    }

    response = {
        'message': None,
        'status': 'OK',
        'id': None,
        'kvt1Base64': None,
        'kvt1Fname': None,
        'kvtList': [
            {
                'kvtBase64': '',
                'kvtFname': '26591010101017J1499101100000000311220182659.KVT',
                'numKvt': 1,
                'finalKvt': 0,
                'status': 1
            },
            {
                'kvtBase64': 'aGVsbG8=',
                'kvtFname': '26591010101017J1499101100000000311220182659_FINAL.KVT',
                'numKvt': 1,
                'finalKvt': 1,
                'status': 1
            }
        ]
    }

    @patch("fiscal_bot.tasks.get_working_datetime")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    def test_check_request_fail_request(self, requests_mock, decode_and_save_data_mock, retry_mock, get_wt_mock):
        get_wt_mock.return_value = datetime(2007, 1, 2, 13, 30)
        retry_mock.side_effect = Retry

        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        request_time = TIMEZONE.localize(datetime(2019, 3, 29, 15, 47))
        requests_mock.post.side_effect = requests.exceptions.ConnectionError()

        with patch("fiscal_bot.tasks.working_days_count_since") as working_days_count_since_mock:
            working_days_count_since_mock.return_value = 0
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=request_time,
                    requests_reties=0
                )
        working_days_count_since_mock.assert_called_once_with(
            request_time, custom_wd=CUSTOM_WORK_DAY, working_weekends_enabled=True
        )
        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)
        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
        )
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.get_working_datetime")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    def test_check_request_fail_status(self, requests_mock, decode_and_save_data_mock, retry_mock, get_wt_mock):
        get_wt_mock.return_value = datetime(2007, 1, 2, 13, 30)
        retry_mock.side_effect = Retry

        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        requests_mock.post.return_value = Mock(
            status_code=502,
            text="Bad Gateway",
            headers={"Retry-After": 10}
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=0
                )

        retry_mock.assert_called_once_with(
            countdown=10
        )
        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
        )
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.get_now")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    def test_check_request_fail_no_report(self, requests_mock, decode_and_save_data_mock, retry_mock, get_now_mock):
        get_now_mock.return_value = TIMEZONE.localize(datetime(2007, 1, 2, 16))
        retry_mock.side_effect = Retry

        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.fail_response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):

            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=0
                )

        retry_mock.assert_called_once_with(
            eta=TIMEZONE.localize(datetime(2007, 1, 3, 9))
        )
        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
        )
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    def test_check_request_success(self, requests_mock, decode_and_save_data_mock):
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=0
            )

        self.assertEqual(
            requests_mock.post.call_args_list,
            [
                call(
                    '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
                    data=request_data,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    proxies=FISCAL_API_PROXIES,
                )
            ]
        )

        self.assertEqual(
            decode_and_save_data_mock.delay.call_args_list,
            [
                call(
                    self.response["kvtList"][-1]["kvtFname"],
                    self.response["kvtList"][-1]["kvtBase64"],
                    supplier["tender_id"],
                    supplier["award_id"],
                )
            ]
        )

    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_check_on_3rd_wd_1(self, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock):
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=0
            )

        requests_mock.post.assert_not_called()
        decode_and_save_data_mock.assert_not_called()
        prepare_receipt_request_mock.delay.assert_called_once_with(
            supplier=supplier,
            requests_reties=1
        )

    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_check_on_3rd_wd_2(self, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock):
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=1
            )

        requests_mock.post.assert_not_called()
        decode_and_save_data_mock.assert_not_called()
        prepare_receipt_request_mock.delay.assert_called_once_with(
            supplier=supplier,
            requests_reties=2
        )

    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    def test_check_on_3rd_wd_3(self, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock):
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=REQUEST_MAX_RETRIES
            )

        requests_mock.post.assert_not_called()
        decode_and_save_data_mock.assert_not_called()
        prepare_receipt_request_mock.delay.assert_not_called()
